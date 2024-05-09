import time
import json
from pathlib import Path
from flask import Flask, request
from detect import run
import uuid
import yaml
from loguru import logger
import os
import boto3
import pymongo

images_bucket = os.environ['BUCKET_NAME']

with open("data/coco128.yaml", "r") as stream:
    names = yaml.safe_load(stream)['names']

app = Flask(__name__)

@app.route('/predict', methods=['POST'])
def predict():
    # Generates a UUID for this current prediction HTTP request. This id can be used as a reference in logs to identify and track individual prediction requests.
    prediction_id = str(uuid.uuid4())

    logger.info(f'prediction: {prediction_id}. start processing')

    # Receives a URL parameter representing the image to download from S3
    img_name = request.args.get('imgName')

    # TODO download img_name from S3, store the local image path in the original_img_path variable.
    #  The bucket name is provided as an env var BUCKET_NAME.
    download_path = '/usr/src/app/downloaded_images'
    s3_client = boto3.client('s3')
    print(f'images/{img_name}')
    s3_client.download_file(
        Bucket=f'{images_bucket}',
        Key=f'images/{img_name}',
        Filename=f'{download_path}/{img_name}'
    )
    original_img_path = f'{download_path}/{img_name}'

    logger.info(f'prediction: {prediction_id}{original_img_path}. Download img completed')

    # Predicts the objects in the image
    run(
        weights='yolov5s.pt',
        data='data/coco128.yaml',
        source=original_img_path,
        project='static/data',
        name=prediction_id,
        save_txt=True
    )

    logger.info(f'prediction: {prediction_id}/{original_img_path}. done')

    # This is the path for the predicted image with labels
    # The predicted image typically includes bounding boxes drawn around the detected objects, along with class labels and possibly confidence scores.
    predicted_img_path = f'static/data/{prediction_id}{original_img_path}'

    # TODO Uploads the predicted image (predicted_img_path) to S3 (be careful not to override the original image).
    s3_client.put_object(
        Body=f'{predicted_img_path}',
        Bucket=f'{images_bucket}',
        Key=f'predicted_images/{img_name}'
    )

    # Parse prediction labels and create a summary
    split_summary_path = Path(f'static/data/{prediction_id}/labels{original_img_path}').stem
    pred_summary_path = Path(f'static/data/{prediction_id}/labels/{split_summary_path}.txt')
    if pred_summary_path.exists():
        with open(pred_summary_path, 'r', encoding="utf-8") as f:
            labels = f.read().splitlines()
            labels = [line.split(' ') for line in labels]
            labels = [{
                'class': names[int(l[0])],
                'cx': float(l[1]),
                'cy': float(l[2]),
                'width': float(l[3]),
                'height': float(l[4]),
            } for l in labels]

        logger.info(f'prediction: {prediction_id}{original_img_path}. prediction summary:\n\n{labels}')
        print('...')

        prediction_summary = {
            '_id': prediction_id,
            'original_img_path': original_img_path,
            'predicted_img_path': predicted_img_path,
            'labels': labels,
            'time': f'{time.time()}'
        }

        # TODO store the prediction_summary in MongoDB
        client = pymongo.MongoClient('mongodb://mongo1:27017,mongo2:27018,mongo3:27019/?replicaSet=mongo-replica-set')
        db = client["docker_project"]
        collection = db["predictions"]
        collection.insert_one(prediction_summary)

        return prediction_summary
    else:
        return f'prediction: {prediction_id}{original_img_path}. prediction result not found', 404


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8081)
