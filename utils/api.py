import httpx
import logging
# from utils.html_utils import num_tokens_from_string

LLAMA_POST_URL = 'http://127.0.0.1:9999/predict/'


def logging_setup():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("logs.log"),
        ]
    )

logging_setup()


if __name__ == '__main__':
    # print(llama3(TEXT))
    pass