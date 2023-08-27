import boto3
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime, timedelta
import csv
import json
import os

#j = json.loads("{\"TimePeriod\":{\"Start\":\"2023-08-21\",\"End\":\"2023-08-27\"},\"Metrics\":[\"BlendedCost\"],\"Granularity\":\"DAILY\",\"GroupBy\":[{\"Type\":\"DIMENSION\",\"Key\":\"SERVICE\"}],\"Filter\":{\"Or\":[{\"Dimensions\":{\"Key\":\"SERVICE\",\"Values\":[\"AWS CloudShell\"]}},{\"Dimensions\":{\"Key\":\"SERVICE\",\"Values\":[\"AmazonCloudWatch\"]}},{\"Dimensions\":{\"Key\":\"SERVICE\",\"Values\":[\"AWS CodeArtifact\"]}},{\"Dimensions\":{\"Key\":\"SERVICE\",\"Values\":[\"CodeBuild\"]}},{\"Dimensions\":{\"Key\":\"SERVICE\",\"Values\":[\"AWS CodeCommit\"]}},{\"Dimensions\":{\"Key\":\"SERVICE\",\"Values\":[\"AWS Cost Explorer\"]}},{\"Dimensions\":{\"Key\":\"SERVICE\",\"Values\":[\"EC2 - Other\"]}},{\"Dimensions\":{\"Key\":\"SERVICE\",\"Values\":[\"Amazon EC2 Container Registry (ECR)\"]}},{\"Dimensions\":{\"Key\":\"SERVICE\",\"Values\":[\"Amazon Elastic Compute Cloud - Compute\"]}},{\"Dimensions\":{\"Key\":\"SERVICE\",\"Values\":[\"Amazon Elastic Container Service for Kubernetes\"]}},{\"Dimensions\":{\"Key\":\"SERVICE\",\"Values\":[\"AWS Key Management Service\"]}},{\"Dimensions\":{\"Key\":\"SERVICE\",\"Values\":[\"Amazon Simple Storage Service\"]}},{\"Dimensions\":{\"Key\":\"SERVICE\",\"Values\":[\"Amazon Simple Email Service\"]}},{\"Dimensions\":{\"Key\":\"SERVICE\",\"Values\":[\"Amazon Simple Notification Service\"]}},{\"Dimensions\":{\"Key\":\"SERVICE\",\"Values\":[\"Tax\"]}},{\"Dimensions\":{\"Key\":\"SERVICE\",\"Values\":[\"Amazon Virtual Private Cloud\"]}}]}}")
# print(j)
##start date to be before end date
end_date = datetime.now().date() - timedelta(days=1)  #todays date -1 
start_date = end_date - timedelta(days=6)  # Fetch data for the last 7 days todaysdate-1-6

ce_client = boto3.client('ce', region_name='us-east-1')
def fetch_cost_usage(start_date, end_date):
      response = ce_client.get_cost_and_usage(
         TimePeriod={
            'Start': start_date.isoformat(),
            'End': end_date.isoformat()
         },
         #  Filter={
         #      "Or":[
         #       {
         #          "Dimensions":{
         #             "Key":"SERVICE",
         #             "Values":[
         #                "AmazonCloudWatch"
         #             ]
         #          }
         #       },
         #       {
         #          "Dimensions":{
         #             "Key":"SERVICE",
         #             "Values":[
         #                "AWS Cost Explorer"
         #             ]
         #          }
         #       }]
         #  },
         Filter={
                  'Dimensions': {
                     'Key': 'LINKED_ACCOUNT',
                     'Values': [
                           '964495499316',    # key is AWS account number
                     ]
                  },
               },
         Granularity='DAILY',
         Metrics=['BlendedCost'],
         GroupBy=[
            # {
            #     'Type': 'DIMENSION',
            #     'Key': 'RESOURCE_ID'
            # },
            {
                  'Type': 'DIMENSION',
                  'Key': 'SERVICE'
            },
            #   {'Type': 'DIMENSION', 'Key': 'LINKED_ACCOUNT'}
         ]
      )
      return response['ResultsByTime']

datas=fetch_cost_usage(start_date,end_date)
#print(datas)
def generate_csv(datas):
    # Generate a CSV file with cost and usage 
    file_name='cost_usage_report.csv'
    csv_filename = file_name
    with open('/tmp/' +csv_filename, 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(['Services','Date','Cost'])
        for result in datas:
            services = result['Groups'][0]['Keys'][0]
            date = result['TimePeriod']
            cost = result['Groups'][0]['Metrics']['BlendedCost']['Amount']
            csv_writer.writerow([services,date,cost])
    return csv_filename

attachment_file=generate_csv(datas)


def lambda_handler(context=None, event=None):

   SENDER = "dantedemon269@gmail.com"
   RECIPIENT = "dantedemon269@gmail.com"
   SUBJECT = "Test Send Mesage with Attachment"
   FILE_NAME = generate_csv(datas)
   TMP_FILE_NAME = '/tmp/' +FILE_NAME
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
   client = boto3.client('ses',region_name='us-east-1')

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
