import telebot
from loguru import logger
import os
import time
from telebot.types import InputFile
from img_proc import Img
import boto3
import requests

images_bucket = os.environ['BUCKET_NAME']
class Bot:

    def __init__(self, token, telegram_chat_url):
        # create a new instance of the TeleBot class.
        # all communication with Telegram servers are done using self.telegram_bot_client
        self.telegram_bot_client = telebot.TeleBot(token)

        # remove any existing webhooks configured in Telegram servers
        self.telegram_bot_client.remove_webhook()
        time.sleep(0.5)

        # set the webhook URL
        self.telegram_bot_client.set_webhook(url=f'{telegram_chat_url}/{token}/', timeout=60)

        logger.info(f'Telegram Bot information\n\n{self.telegram_bot_client.get_me()}')

    def send_text(self, chat_id, text):
        self.telegram_bot_client.send_message(chat_id, text)

    def send_text_with_quote(self, chat_id, text, quoted_msg_id):
        self.telegram_bot_client.send_message(chat_id, text, reply_to_message_id=quoted_msg_id)

    def is_current_msg_photo(self, msg):
        return 'photo' in msg

    def download_user_photo(self, msg):
        """
        Downloads the photos that sent to the Bot to `photos` directory (should be existed)
        :return:
        """
        if not self.is_current_msg_photo(msg):
            raise RuntimeError(f'Message content of type \'photo\' expected')

        file_info = self.telegram_bot_client.get_file(msg['photo'][-1]['file_id'])
        data = self.telegram_bot_client.download_file(file_info.file_path)
        folder_name = file_info.file_path.split('/')[0]

        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        with open(file_info.file_path, 'wb') as photo:
            photo.write(data)

        return file_info.file_path

    def send_photo(self, chat_id, img_path):
        if not os.path.exists(img_path):
            raise RuntimeError("Image path doesn't exist")

        self.telegram_bot_client.send_photo(
            chat_id,
            InputFile(img_path)
        )

    def handle_message(self, msg):
        """Bot Main message handler"""
        logger.info(f'Incoming message: {msg}')
        self.send_text(msg['chat']['id'], f'Your original message: {msg["text"]}')


class ImageProcessingBot(Bot):
    def __init__(self, token, telegram_chat_url):
        super().__init__(token, telegram_chat_url)
        self.media_group = []

    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')
        if self.is_current_msg_photo(msg):
            try:
                is_concat = False
                # checks if 2 photos had sent
                if msg["media_group_id"]:
                    self.media_group.append(msg)
                if len(self.media_group) == 2:
                    # checks if one of the photos had the caption concat
                    if self.media_group[0]["caption"] == "concat" or self.media_group[1]["caption"] == "concat":
                        path_to_image1 = self.download_user_photo(self.media_group[0])
                        image1 = Img(path_to_image1)
                        path_to_image2 = self.download_user_photo(self.media_group[1])
                        image2 = Img(path_to_image2)
                        image1.concat(image2)
                        path_to_filtered = image1.save_img()
                        self.send_photo(msg['chat']['id'], path_to_filtered)
                        self.media_group = []
                return
            except:
                try:
                    # check if the photo has caption
                    photo_filter = msg["caption"]
                    photo_filter = photo_filter.lower()
                except:
                    self.send_text(msg['chat']['id'], f'You didn\'t mention filter to apply.')
                    return
                try:
                    if photo_filter == 'detect':
                        # apply detection if detect filter had mentioned
                        photo_path = self.download_user_photo(msg)

                        # upload the downloaded photo to S3
                        s3_client = boto3.client('s3')
                        img_name = os.path.basename(photo_path)
                        s3_client.upload_file(
                            Bucket=f'{images_bucket}',
                            Key=f'images/{img_name}',
                            Filename=f'{photo_path}'
                        )

                        # send an HTTP request to the `yolo5` service for prediction
                        predict = requests.post(f'http://yolo5:8081/predict?imgName={img_name}')

                        # send the returned results to the Telegram end-user
                        data = predict.json()
                        objects = []
                        labels = data['labels']
                        for label in labels:
                            objects.append(label['class'])

                        counter = dict.fromkeys(objects, 0)
                        for val in objects:
                            counter[val] += 1
                        print(f'Detected Objects: \n{counter}')
                        self.send_text((msg['chat']['id']), text=f'Detected Objects: \n{counter}')
                    else:
                        # apply filter for image processing if filter exists
                        path_to_image = self.download_user_photo(msg)
                        image = Img(path_to_image)
                        apply_filter = image.find_filter(photo_filter)
                        if apply_filter is False:
                            self.send_text((msg['chat']['id']), f'The filter you mentioned doesn\'t exist.')
                            return
                        path_to_filtered = image.save_img()
                        self.send_photo((msg['chat']['id']), path_to_filtered)
                except:
                    self.send_text((msg['chat']['id']), f'Unknown error occurred, please try again')
        else:
            self.send_text((msg['chat']['id']), f'for filtering photo, please send a photo.')


# class ObjectDetectionBot(Bot):
#     def handle_message(self, msg):
#         logger.info(f'Incoming message: {msg}')
#
#         if self.is_current_msg_photo(msg):
#             photo_path = self.download_user_photo(msg)
#
#             # upload the downloaded photo to S3
#             s3_client = boto3.client('s3')
#             img_name = os.path.basename(photo_path)
#             s3_client.upload_file(
#                 Bucket=f'{images_bucket}',
#                 Key=f'images/{img_name}',
#                 Filename=f'{photo_path}'
#             )
#
#             # send an HTTP request to the `yolo5` service for prediction
#             predict = requests.post(f'http://yolo5:8081/predict?imgName={img_name}')
#
#             # send the returned results to the Telegram end-user
#             data = predict.json()
#             objects = []
#             labels = data['labels']
#             for label in labels:
#                 objects.append(label['class'])
#
#             counter = dict.fromkeys(objects, 0)
#             for val in objects:
#                 counter[val] += 1
#             print(f'Detected Objects: \n{counter}')
#             self.send_text((msg['chat']['id']),text=f'Detected Objects: \n{counter}')