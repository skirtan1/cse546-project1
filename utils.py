import logging
import io

def safe_upload(client, bucket, key, data, content_type=""):
    """Safely upload fileobj to s3 bucket

    :param bucket: bucket client obj
    :type bucket: boto3.S3.Bucket
    :param key: Key of the obj
    :type key: str
    :param data: File data to upload
    :type data: binary str
    :return: True if operation successfull
    :rtype: bool
    """
    try:
        client.put_object(Bucket=bucket, Body=data.getvalue(), Key=key, Metadata={"Content-Type": content_type})
        logging.info("Uploaded obj {}\
                     to s3 bucket {}\
                    ".format(
                        key, bucket
                    ))
        return True
    except Exception as e:
        logging.error("Caught exeception {}\
                     while uploading obj {} to\
                     s3 bucket: {}".format(
                     e, key, bucket
                    ))
        return False
    
def safe_download(client, bucket, key):
    """Safely download fileobj from s3 bucket

    :param bucket: bucket client object
    :type bucket: boto3.S3.Bucket
    :param key: Key of the object
    :type key: str
    :return: binary file data if successfull else None
    :rtype: io.BytesIO
    """
    data = io.BytesIO()
    try:
        client.download_fileobj(Bucket=bucket, Key=key, Fileobj=data)
        logging.info("Download obj {}\
                     from s3 bucket {}\
                     ".format(
                        key, bucket
                     ))
    except Exception as e:
        logging.error("Caught exception {}\
                       while downloading obj {}\
                       from s3 bucket {}".format(
                        e, key, bucket
                       ))
    return data