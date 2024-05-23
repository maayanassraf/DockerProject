# The Polybot Service: Docker Project [![][autotest_badge]][autotest_workflow]

## Background

This docker project based on the previous [python project](https://github.com/maayanassraf/ImageProcessingService), there I developed a chatbot application which applies filters to images sent by users to a Telegram bot.

In this project, I extended the service to detect objects in images, and send the results to clients.

The service consisted by multiple containerized microservices, as follows: 

- `polybot`: Telegram Bot app.
- `yolo5`: Image object detection container based on the Yolo5 pre-train deep learning model.
- `mongo`: MongoDB cluster to store data.

## Flow For Using The Service

1. Clients send images to the Telegram bot named **ImageProcessingBot** with desired filter.
2. The `polybot` microservice receives the message, downloads the image to the local file system.
3. If the filter mentioned is "detect", the `polybot` microservice uploads the image to an S3 bucket. 
4. The `polybot` microservice then initiates an HTTP request to the `yolo5` microservice, and waits for the response. 
5. Once the response arrived, the `polybot` microservice parse the returned JSON and sends the results to the client.
6. If the filter mentioned wasn't "detect", the `polybot` microservice will pass steps 3-5 and will apply filter as 
described in the [python project](https://github.com/maayanassraf/ImageProcessingService).

## Guidelines

### The `mongo` microservice

In this project, MongoDB will be used to save the prediction summary done by the yolo5 microservice.
There are 3 mongo containers in a replica-set.
The replica-set creates automatically with a 4th container, which running a bash
script that initiate the replica-set and then ends.

### The `yolo5` microservice

[YoloV5](https://github.com/ultralytics/yolov5) is a state-of-the-art object detection AI model. In this project,
the version that has been used is a lightweight model that can detect [80 objects](https://github.com/ultralytics/yolov5/blob/master/data/coco128.yaml) while it's running on your old, poor, CPU machine. 

The service files can be found under the `yolo5` directory.
The `yolo5/app.py` file is a Flask-based webserver, with an endpoint `/predict`, which can be used to predict objects in a given image, as follows:

```text
localhost:8081/predict?imgName=street.jpeg
```

The `imgName` query parameter value (`street.jpeg` in the above example) represents an image name stored in an **S3 bucket**. 
The `yolo5` service then downloads the image from the S3 bucket and detects objects in it. 


```bash
curl -X POST localhost:8081/predict?imgName=street.jpeg
```

Here is an image and the corresponding results summary:

<img src="https://alonitac.github.io/DevOpsTheHardWay/img/docker_project_street.jpeg" width="60%">

```json
{
    "prediction_id": "9a95126c-f222-4c34-ada0-8686709f6432",
    "original_img_path": "data/images/street.jpeg",
    "predicted_img_path": "static/data/9a95126c-f222-4c34-ada0-8686709f6432/street.jpeg",
    "labels": [
      {
        "class": "person",
        "cx": 0.0770833,
        "cy": 0.673675,
        "height": 0.0603291,
        "width": 0.0145833
      },
      {
        "class": "traffic light",
        "cx": 0.134375,
        "cy": 0.577697,
        "height": 0.0329068,
        "width": 0.0104167
      },
      {
        "class": "potted plant",
        "cx": 0.984375,
        "cy": 0.778793,
        "height": 0.095064,
        "width": 0.03125
      },
      {
        "class": "stop sign",
        "cx": 0.159896,
        "cy": 0.481718,
        "height": 0.0859232,
        "width": 0.053125
      },
      {
        "class": "car",
        "cx": 0.130208,
        "cy": 0.734918,
        "height": 0.201097,
        "width": 0.108333
      },
      {
        "class": "bus",
        "cx": 0.285417,
        "cy": 0.675503,
        "height": 0.140768,
        "width": 0.0729167
      }
    ],
    "time": 1692016473.2343626
}
```

The model detected a _person_, _traffic light_, _potted plant_, _stop sign_, _car_, and a _bus_. Try it yourself with different images.

### The `polybot` microservice

The polybot microservice handles all the incoming messages to the Telegram bot, 
based on the caption attached to the photo that sent. in addition to all the filters
that implemented in the [python project](https://github.com/maayanassraf/ImageProcessingService), 
'detect' in the caption will activate the yolo5 microservice for detection objects in the photo.


Here is an end-to-end example of how it may look like:

<img src="https://github.com/maayanassraf/DockerProject/blob/main/example.jpg" width="30%">

## Deployment

To simplify the deployment process, I had created a Docker Compose project in the `docker-compose.yaml` file. 
This file enables to launch all the microservices with a single command: `docker compose up`.

To ensure flexibility and avoid manual editing of the `docker-compose.yaml` ,
I specified the values that change frequently as environment variables for the Docker Compose project via a `.env` file.

#### Deployment notes

- The `yolo5` and `polybot` images had pushed to private ECR repository. In deployment the images taken from there. 
- The project uses a single `medium` Ubuntu EC2 instance with 20GB disk and a s3 bucket.
- The polybot exposed to Telegram servers by using Ngrok, as done in the previous project.
- An IAM role is attached to the EC2 instance with the relevant permissions.


## CI/CD pipeline using GitHub Actions

The CI/CD is triggered automatically via GitHub Actions, by pushing code to branch main.

This CI/CD contains 2 workflows (`service-deploy.yaml` and `project_auto_testing.yaml`).
Those workflows using repository secrets- `TELEGRAM_BOT_TOKEN`, `EC2_SSH_PRIVATE_KEY`, 
`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.

### The CI/CD Process

1. The CI/CD pipline is triggered by pushing code to branch `main`.
2. First, the `service-deploy.yaml` workflow starts.
3. In the `PolybotBuild` step - the workflow build `polybot` image and pushes it to the existing ECR repository.
4. In the `Yolo5Build` step - the workflow build `yolo5` image and pushes it to the existing ECR repository.
5. In the `Deploy Docker compose project` step - the workflow replaces the .env file with new 
variables that had changed (e.g. the images tags) and recreates the docker project by `docker compose down` 
and then, with all changes runs `docker compose up`.
6. Afterward, the `project_auto_testing.yaml` workflow will run and will check if after the 
`service-deploy.yaml` workflow, the service is running properly.


[DevOpsTheHardWay]: https://github.com/alonitac/DevOpsTheHardWay
[onboarding_tutorial]: https://github.com/alonitac/DevOpsTheHardWay/blob/main/tutorials/onboarding.md
[autotest_badge]: ../../actions/workflows/project_auto_testing.yaml/badge.svg?event=push
[autotest_workflow]: ../../actions/workflows/project_auto_testing.yaml/
[fork_github]: https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo#forking-a-repository
[clone_pycharm]: https://www.jetbrains.com/help/pycharm/set-up-a-git-repository.html#clone-repo
[github_actions]: ../../actions

[PolybotServicePython]: https://github.com/alonitac/ImageProcessingService
[docker_project_street]: https://alonitac.github.io/DevOpsTheHardWay/img/docker_project_street.jpeg
[docker_project_polysample]: https://alonitac.github.io/DevOpsTheHardWay/img/docker_project_polysample.jpg
