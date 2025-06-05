# imaging-plaza-search

A microservice for fetching relevant softwares to a certain search term + filters input. This service will retrieve software from GraphDB and then perform a fuzzy search using [Fuzon](https://github.com/sdsc-ordes/fuzon).

## How to use it?

It's necessary to send a `post` request to the API endpoint (`URL/v1/search`) with a body following this example. If you want to try you can do it directly in `URL/docs` by clicking in the `Try it out` button. 

```json
{
    "search": "deep",
    "filters": [
        {
            "key": "programmingLanguage",
            "schema_key": "schema:programmingLanguage",
            "value": [
                "Python"
            ]
        },
        {
            "key": "featureList",
            "schema_key": "schema:featureList",
            "value": [
                "Object detection"
            ]
        }
    ]
}
```

The reply should looks like: 

```json
[
  {
    "label": "DeepLabCut",
    "uri": "<https://github.com/DeepLabCut/DeepLabCut>"
  },
  {
    "label": "stardist",
    "uri": "<https://github.com/stardist/stardist>"
  },
  {
    "label": "spotiflow",
    "uri": "<https://github.com/weigertlab/spotiflow>"
  },
  {
    "label": "DEFCoN",
    "uri": "<https://github.com/LEB-EPFL/DEFCoN>"
  },
  {
    "label": "detection-attributes-fields",
    "uri": "<https://github.com/vita-epfl/detection-attributes-fields>"
  },
  {
    "label": "butterflydetector",
    "uri": "<https://github.com/vita-epfl/butterflydetector>"
  }
]
```

## How to deploy it?

First define the env variables needed to connect to graphDB. You can copy and rename `.env.dist` into `.env`.

### Deploy with docker using Just

If you have just available you can build and run the image as follows:

```bash
just image build
```

```bash
just image run
```

Then connect to `localhost:7123`. The port is hardcoded in `tools/just/image.just`

### Deploy directly with docker

If you prefer you can run this directly with docker

```bash
docker build -t imaging-plaza-search -f tools/image/Dockerfile .
```

And then run:

```bash
docker run --rm --name imaging-plaza-search -p 7123:15400 --env-file .env imaging-plaza-search
```

## How to develop?

To develop and see changes in real time you can mount the source folder into docker like this:

```bash
docker run --rm --name imaging-plaza-search -p 7123:15400 -v ./src/:/app/src --env-file .env imaging-plaza-search
```

## Credits 

This MS has been developed by the Swiss Data Science Center. 