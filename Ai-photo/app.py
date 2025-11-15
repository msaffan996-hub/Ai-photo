# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, jsonify
from werkzeug.utils import secure_filename
from face_swap import merge_faces

UPLOAD_FOLDER = 'uploads'
TARGETS_FOLDER = os.path.join(UPLOAD_FOLDER, 'targets')
RESULTS_FOLDER = os.path.join(UPLOAD_FOLDER, 'results')
ALLOWED_EXT = {'png','jpg','jpeg'}

os.makedirs(TARGETS_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TARGETS_FOLDER'] = TARGETS_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER
app.secret_key = 'super-secret-key'  # غيّرها قبل النشر

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXT

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/capture')
def capture():
    return render_template('capture.html')

@app.route('/select', methods=['GET','POST'])
def select():
    if request.method == 'POST':
        # رفع صورة هدف من المستخدم
        file = request.files.get('target_file')
        if file and allowed_file(file.filename):
            fname = secure_filename(file.filename)
            path = os.path.join(app.config['TARGETS_FOLDER'], fname)
            file.save(path)
            return redirect(url_for('merge', target=os.path.basename(path)))
        flash('خطأ في رفع الصورة. تأكد من النوع (png/jpg/jpeg).')
        return redirect(url_for('select'))
    # عرض الصور الجاهزة من المجلد
    targets = [f for f in os.listdir(app.config['TARGETS_FOLDER']) if allowed_file(f)]
    return render_template('select.html', targets=targets)

@app.route('/upload_capture', methods=['POST'])
def upload_capture():
    # تُرسل الصورة الملتقطة كـ base64 من الجافا سكربت
    data_url = request.form.get('image_data')
    import base64, re
    imgstr = re.search(r'base64,(.*)', data_url).group(1)
    imagedata = base64.b64decode(imgstr)
    fname = 'capture_{}.png'.format(len(os.listdir(app.config['RESULTS_FOLDER'])) + 1)
    path = os.path.join(app.config['RESULTS_FOLDER'], fname)  # مؤقتاً نحفظ في results ثم نستخدمه
    with open(path, 'wb') as f:
        f.write(imagedata)
    # رد مع مسار الصورة الملتقطة
    return jsonify({'capture': fname})

@app.route('/merge')
def merge():
    # يَستقبل اسم ملف الهدف (target) واسم ملف الـ capture (capture)
    target = request.args.get('target')
    capture = request.args.get('capture')
    if not target or not capture:
        flash('مطلوب صورة الهدف وصورة الالتقاط.')
        return redirect(url_for('select'))
    target_path = os.path.join(app.config['TARGETS_FOLDER'], secure_filename(target))
    capture_path = os.path.join(app.config['RESULTS_FOLDER'], secure_filename(capture))

    # النتيجة اسم ملف جديد
    result_name = f"result_{secure_filename(capture)}_on_{secure_filename(target)}.png"
    result_path = os.path.join(app.config['RESULTS_FOLDER'], result_name)
    try:
        merge_faces(capture_path, target_path, result_path)
    except Exception as e:
        flash('حدث خطأ أثناء الدمج: ' + str(e))
        return redirect(url_for('select'))

    return redirect(url_for('result', filename=os.path.basename(result_path)))

@app.route('/result/<filename>')
def result(filename):
    return render_template('result.html', filename=filename)

@app.route('/uploads/results/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['RESULTS_FOLDER'], filename)

@app.route('/gallery')
def gallery():
    images = [f for f in os.listdir(app.config['RESULTS_FOLDER']) if allowed_file(f)]
    return render_template('gallery.html', images=images)

@app.route('/settings')
def settings():
    # إعدادات بسيطة الآن (يمكن حفظها لاحقاً في ملف/DB)
    return render_template('settings.html')

@app.route('/help')
def help_page():
    return render_template('help.html')

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True)
