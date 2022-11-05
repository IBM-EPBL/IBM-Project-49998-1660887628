from flask import Flask,render_template,request
from flask_sqlalchemy import SQLAlchemy
app=Flask(__name__)


@app.route('/')
def hello():
    return render_template('index.html')
@app.route('/result', methods=['GET', 'POST'])
def result():
    email=request.form.get('email')
    gender=request.form.get('genderm')
    typeofuse=request.form.get('choice')

    return render_template('result.html',email=email,gender=gender,typeofuse=typeofuse)
if __name__ =='__main__':
    app.run()