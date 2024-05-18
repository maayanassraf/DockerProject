from pathlib import Path
from matplotlib.image import imread, imsave
import random


def rgb2gray(rgb):
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    gray = 0.2989 * r + 0.5870 * g + 0.1140 * b
    return gray


class Img:

    def __init__(self, path):
        """
        Do not change the constructor implementation
        """
        self.path = Path(path)
        self.data = rgb2gray(imread(path)).tolist()

    def save_img(self):
        """
        Do not change the below implementation
        """
        new_path = self.path.with_name(self.path.stem + '_filtered' + self.path.suffix)
        imsave(new_path, self.data, cmap='gray')
        return new_path

    def blur(self, blur_level=16):

        height = len(self.data)
        width = len(self.data[0])
        filter_sum = blur_level ** 2

        result = []
        for i in range(height - blur_level + 1):
            row_result = []
            for j in range(width - blur_level + 1):
                sub_matrix = [row[j:j + blur_level] for row in self.data[i:i + blur_level]]
                average = sum(sum(sub_row) for sub_row in sub_matrix) // filter_sum
                row_result.append(average)
            result.append(row_result)

        self.data = result

    def contour(self):
        for i, row in enumerate(self.data):
            res = []
            for j in range(1, len(row)):
                res.append(abs(row[j-1] - row[j]))

            self.data[i] = res

    def rotate(self):
        result = []
        temp = zip(*self.data)
        for i in temp:
            reversed_i = list(i[::-1])
            result.append(reversed_i)
        self.data = result

    def salt_n_pepper(self):
        result = []
        for row in self.data:
            row_result = []
            for item in row:
                pix_random = random.random()
                if pix_random < 0.2:
                    row_result.append(255)
                elif pix_random > 0.8:
                    row_result.append(0)
                else:
                    row_result.append(item)
            result.append(row_result)
        self.data = result

    def concat(self, other_img, direction='horizontal'):
        height_img1 = len(self.data)
        height_img2 = len(other_img.data)
        width_img1 = len(self.data[0])
        width_img2 = len(other_img.data[0])
        if height_img1 != height_img2 or width_img1 != width_img2:
            raise RuntimeError("the images aren't in the same size, can't concatenate")
        result = []
        for row in range(len(self.data)):
            new_row = self.data[row] + other_img.data[row]
            result.append(new_row)
        self.data = result

    def segment(self):
        result = []
        for row in self.data:
            row_result = []
            for item in row:
                if item > 100:
                    row_result.append(255)
                else:
                    row_result.append(0)
            result.append(row_result)
        self.data = result

    def find_filter(self, msg):
        all_filters = {'contour': 'self.contour()', 'rotate': 'self.rotate()', 'segment': 'self.segment()', 'salt and pepper': 'self.salt_n_pepper()'}
        is_existing = False
        if 'blur' in msg:
            blur_level = 16
            is_existing = True
            for word in msg.split():
                try:
                    blur_level = int(word)
                except:
                    break
            self.blur(blur_level=blur_level)
        else:
            for key in all_filters:
                if key in msg:
                    is_existing = True
                    eval(all_filters[key])
                    return
        if not is_existing:
            return False