import os.path
import boto3
import email
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


s3 = boto3.client("s3")

def lambda_handler(event, context):
    # Replace sender@example.com with your "From" address.
    # This address must be verified with Amazon SES.
    SENDER = ""

    # Replace recipient@example.com with a "To" address. If your account 
    # is still in the sandbox, this address must be verified.
    RECIPIENT = ""

    # Specify a configuration set. If you do not want to use a configuration
    # set, comment the following variable, and the 
    # ConfigurationSetName=CONFIGURATION_SET argument below.
    # CONFIGURATION_SET = "ConfigSet"

    AWS_REGION = "us-east-1"
    SUBJECT = "Test Send Mesage with Attachment"

    # This is the start of the process to pull the files we need from the S3 bucket into the email.
    # Get the records for the triggered event
    FILEOBJ = event["Records"][0]
    # Extract the bucket name from the records for the triggered event
    BUCKET_NAME = str(FILEOBJ['s3']['bucket']['name'])
    # Extract the object key (basicaly the file name/path - note that in S3 there are 
    # no folders, the path is part of the name) from the records for the triggered event
    KEY = str(FILEOBJ['s3']['object']['key'])

    # extract just the last portion of the file name from the file. This is what the file
    # would have been called prior to being uploaded to the S3 bucket
    FILE_NAME = os.path.basename(KEY) 

    # Using the file name, create a new file location for the lambda. This has to
    # be in the tmp dir because that's the only place lambdas let you store up to
    # 500mb of stuff, hence the '/tmp/'+ prefix
    TMP_FILE_NAME = '/tmp/' +FILE_NAME

    # Download the file/s from the event (extracted above) to the tmp location
    s3.download_file(BUCKET_NAME, KEY, TMP_FILE_NAME)

    # Make explicit that the attachment will have the tmp file path/name. You could just
    # use the TMP_FILE_NAME in the statments below if you'd like.
    ATTACHMENT = TMP_FILE_NAME

    # The email body for recipients with non-HTML email clients.
    BODY_TEXT = "Hello,\r\nPlease see the attached file related to recent submission."

    # The HTML body of the email.
    BODY_HTML = """\
    <html>
    <head></head>
    <body>
    <h1>Hello!</h1>
    <p>Please see the attached file related to recent submission.</p>
    </body>
    </html>
    """

    # The character encoding for the email.
    CHARSET = "utf-8"

    # Create a new SES resource and specify a region.
    client = boto3.client('ses',region_name=AWS_REGION)

    # Create a multipart/mixed parent container.
    msg = MIMEMultipart('mixed')
    # Add subject, from and to lines.
    msg['Subject'] = SUBJECT 
    msg['From'] = SENDER 
    msg['To'] = RECIPIENT

    # Create a multipart/alternative child container.
    msg_body = MIMEMultipart('alternative')

    # Encode the text and HTML content and set the character encoding. This step is
    # necessary if you're sending a message with characters outside the ASCII range.
    textpart = MIMEText(BODY_TEXT.encode(CHARSET), 'plain', CHARSET)
    htmlpart = MIMEText(BODY_HTML.encode(CHARSET), 'html', CHARSET)

    # Add the text and HTML parts to the child container.
    msg_body.attach(textpart)
    msg_body.attach(htmlpart)

    # Define the attachment part and encode it using MIMEApplication.
    att = MIMEApplication(open(ATTACHMENT, 'rb').read())

    # Add a header to tell the email client to treat this part as an attachment,
    # and to give the attachment a name.
    att.add_header('Content-Disposition','attachment',filename=os.path.basename(ATTACHMENT))

    # Attach the multipart/alternative child container to the multipart/mixed
    # parent container.
    msg.attach(msg_body)

    # Add the attachment to the parent container.
    msg.attach(att)
    print(msg)
    try:
        #Provide the contents of the email.
        response = client.send_raw_email(
            Source=SENDER,
            Destinations=[
                RECIPIENT
            ],
            RawMessage={
                'Data':msg.as_string(),
            },
    #        ConfigurationSetName=CONFIGURATION_SET
        )
    # Display an error if something goes wrong. 
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])
