import ibm_boto3, ibm_db
import uuid
import requests, json
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from datetime import datetime
from clarifai_grpc.channel.clarifai_channel import ClarifaiChannel
from clarifai_grpc.grpc.api import service_pb2_grpc
from clarifai_grpc.grpc.api import service_pb2, resources_pb2
from clarifai_grpc.grpc.api.status import status_code_pb2
from ibm_botocore.client import Config, ClientError
from passlib.hash import sha256_crypt
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
stub = service_pb2_grpc.V2Stub(ClarifaiChannel.get_grpc_channel())
SENDGRID_API_KEY = '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'
conn= ibm_db.connect("DATABASE=bludb;HOSTNAME=21fecfd8-47b7-4937-840d-d791d0218660.bs2io90l08kqb1od8lcg.databases.appdomain.cloud;PORT=31864;SECURITY=SSL;SSLServerCertificate=DigiCertGlobalRootCA.crt;UID=wtm19331;PWD=PqN1qLnqGxUVePyP",'','')
COS_ENDPOINT = "https://s3.jp-tok.cloud-object-storage.appdomain.cloud"
COS_API_KEY_ID = "6j6IEFB66TlzbqHpfbUaaNA9ej3_dCjYI0WzDb3dBvt5"
COS_INSTANCE_CRN = "crn:v1:bluemix:public:cloud-object-storage:global:a/040e6e55879742a39df9744b96d97e3f:ebaca05e-1864-4b3c-9aa1-e363d67806aa::"
cos = ibm_boto3.resource("s3",
    ibm_api_key_id=COS_API_KEY_ID,
    ibm_service_instance_id=COS_INSTANCE_CRN,
    config=Config(signature_version="oauth"),
    endpoint_url=COS_ENDPOINT
)
app = Flask(__name__)
app.secret_key = "XYZ"

@app.route('/styles/<path:path>')
def send_report(path):
    return send_from_directory('styles', path)

@app.route('/signUpForm')
def form():
    return render_template('signup.html')

@app.route('/home')
def home():
    id = session['id']
    totalCalories = 0
    resultSet = []
    date = datetime.today().strftime('%Y-%m-%d')
    select_sql= "SELECT * FROM FOOD_DETAILS WHERE USER_ID= '"+str(id)+"' AND DATE(UPLOADED_DATE_TIME) = '"+date+"'"
    select_stmt= ibm_db.exec_immediate(conn, select_sql)
    dictionary = ibm_db.fetch_assoc(select_stmt)
    while dictionary != False:
        resultSet.append(dictionary)
        dictionary = ibm_db.fetch_assoc(select_stmt)
    print(resultSet)
    for i in range(len(resultSet)):
        totalCalories += resultSet[i]['CALORIES']
    return render_template('home.html', data=totalCalories)

@app.route('/uploadFood')
def uploadFood():
    return render_template('upload.html')

@app.route('/loginForm')
def loginForm():
    return render_template('login.html')

@app.route('/signup', methods = ['POST', 'GET'])
def signup():
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    email_id = request.form['email_id']
    phone_number = request.form['phone_number']
    username = request.form['username']
    password = request.form['password']
    password = sha256_crypt.hash(password)
    insert_sql= "INSERT INTO WTM19331.USERS (USERNAME,PASSWORD,FIRST_NAME,LAST_NAME,EMAIL_ID,PHONE_NUMBER) VALUES('"+username+"', '"+password+"', '"+first_name+"', '"+last_name+"', '"+email_id+"', '"+phone_number+"')"
    print(insert_sql)
    insert_stmt= ibm_db.exec_immediate(conn,insert_sql)
    message = Mail(
        from_email='elatejeshwarcse2019@citchennai.net',
        to_emails=email_id,
        subject='Hello from Nutrition Assistant Team!',
        html_content='<strong> We are delighted to have you on board and hope to help you in your day to day fitness and food intake goals!</strong>')
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e.message)
    return render_template('login.html')

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    session.pop('id')
    return render_template('login.html')    

@app.route('/login', methods = ['POST', 'GET'])
def login():
    username = request.form['username']
    password = request.form['password']
    select_sql= "SELECT * FROM USERS WHERE USERNAME = '"+username+"'" 
    select_stmt= ibm_db.exec_immediate(conn, select_sql)
    dictionary = ibm_db.fetch_assoc(select_stmt)
    if(dictionary):
        if(sha256_crypt.verify(password, dictionary['PASSWORD'])):
            session['id'] = dictionary['ID']
            return redirect(url_for('home'))
        else:
            return render_template('login.html', status="incorrectPassword")
    else:
        return render_template('login.html', status="unknownFailure")

@app.route('/foodHistory')
def foodHistory():
    id = session['id']
    resultSet = []
    date = datetime.today().strftime('%Y-%m-%d')
    select_sql= "SELECT * FROM FOOD_DETAILS WHERE USER_ID= '"+str(id)+"' ORDER BY UPLOADED_DATE_TIME DESC"
    select_stmt= ibm_db.exec_immediate(conn, select_sql)
    dictionary = ibm_db.fetch_assoc(select_stmt)
    while dictionary != False:
        resultSet.append(dictionary)
        dictionary = ibm_db.fetch_assoc(select_stmt)
    for i in range(len(resultSet)):
        date_time = resultSet[i]['UPLOADED_DATE_TIME']
        d = date_time.strftime("%d %b, %Y")
        resultSet[i]['UPLOADED_DATE_TIME'] = d
    print(resultSet)  
    return render_template('foodHistory.html', data=resultSet)

@app.route('/profile', methods=['POST','GET'])
def profile():
    id = session['id']
    select_sql= "SELECT * FROM USERS WHERE ID = '"+str(id)+"'" 
    select_stmt= ibm_db.exec_immediate(conn, select_sql)
    dictionary = ibm_db.fetch_assoc(select_stmt)
    if(dictionary):
        print(dictionary)
        return render_template('profile.html', data=dictionary)

@app.route('/upload', methods=['POST', 'GET'])
def upload():
    if(request.method == 'POST'):
        bucket = 'nutrition-assistant-food-details'
        name_file = uuid.uuid4().hex
        f = request.files['file']
        print(f)
        multi_part_upload(bucket, name_file, f)
        id = session['id']
        image_url = 'https://s3.jp-tok.cloud-object-storage.appdomain.cloud/'+bucket+'/'+name_file
        #Clarifai API Call
        CLARIFAI_API_KEY = "517365bb2aa54f1e81b10c6beb05af4a"
        APPLICATION_ID = "search-test"
        metadata = (("authorization", f"Key {CLARIFAI_API_KEY}"),)
        apiRequest = service_pb2.PostModelOutputsRequest(
            # This is the model ID of a publicly available General model. You may use any other public or custom model ID.
            model_id="food-item-v1-recognition",
            user_app_id=resources_pb2.UserAppIDSet(app_id=APPLICATION_ID),
            inputs=[
                resources_pb2.Input(
                    data=resources_pb2.Data(image=resources_pb2.Image(url=image_url))
                )
            ],
        )
        response = stub.PostModelOutputs(apiRequest, metadata=metadata)
        if response.status.code != status_code_pb2.SUCCESS:
            print(response)
            raise Exception(f"Request failed, status code: {response.status}")
        print(response.outputs[0].data.concepts[0].name)
        targetFoodItem = response.outputs[0].data.concepts[0].name
        #RapidAPI Calorieninjas API Call
        calorieApiURL = "https://calorieninjas.p.rapidapi.com/v1/nutrition"
        querystring = {"query":targetFoodItem}
        headers = {
	        "X-RapidAPI-Key": '4c91d633camsh5f6167437f10c9bp1d5217jsnf46fc8764733',
	        "X-RapidAPI-Host": 'calorieninjas.p.rapidapi.com'
        }
        calorieApiResponse = requests.request("GET", calorieApiURL, headers=headers, params=querystring)
        calorieApiResponseDict = json.loads(calorieApiResponse.text)
        print(calorieApiResponseDict)
        targetFoodCalories = calorieApiResponseDict['items'][0]['calories']
        insert_sql = "INSERT INTO WTM19331.FOOD_DETAILS (USER_ID,FOOD_COS_NAME,CALORIES,UPLOADED_DATE_TIME,FOOD_NAME) VALUES('"+str(id)+"', '"+name_file+"', '"+str(targetFoodCalories)+"', now(), '"+targetFoodItem+"')"
        print(insert_sql)
        insert_stmt= ibm_db.exec_immediate(conn,insert_sql)
        return render_template('food_detail.html', data=calorieApiResponseDict, image_url=image_url, targetFoodItem=targetFoodItem)

    if(request.method == 'GET'):
        return render_template('upload.html')

def multi_part_upload(bucket_name, item_name, file):
    print(cos)
    print(bucket_name, item_name, file)
    try:
        print('Starting file transfer for ',item_name,' to bucket ',bucket_name)

        #set 5MB chunks
        part_size = 1024 * 1024 * 5

        #set threshold to 15MB
        file_threshold = 1024 * 1024 * 15

        #set the transfer threshold and chunk size
        transfer_config = ibm_boto3.s3.transfer.TransferConfig(
            multipart_threshold= file_threshold,
            multipart_chunksize= part_size
        )

        #The upload_fileobj method will automatically exwcute a multi-part upload in 5MB chunks
        cos.Object(bucket_name, item_name).upload_fileobj(
            Fileobj = file,
            Config = transfer_config
        )
        print("Transfer for [0] completed!\n".format(item_name))
    except ClientError as be:
        print("CLIENT ERROR: ",be)
    except Exception as e:
        print("Unable to complete multipart upload : ", e)

app.run(host='localhost', port=5000)
if __name__ == '__main__':
    app.debug = True
    app.run()