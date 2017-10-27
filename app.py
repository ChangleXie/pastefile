# -*- coding:utf-8 -*-
import os
from werkzeug import SharedDataMiddleware
from flask import abort, Flask, request, jsonify, redirect, send_file

from ext import db, mako, render_template
from models import PasteFile
from utils import get_file_path, humanize_bytes

ONE_MONTH =60 * 60 * 24 * 30

app = Flask(__name__)
app.config.from_object('config')

app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
    '/i/': get_file_path()
})

mako.init_app(app)
db.init_app(app)


@app.route('/r/<img_hash>')
def rsize(img_hash):
    w = request.form.args['w']
    h = request.form.args['h']

    old_paste = PasteFile.get_by_filehash(img_hash)
    new_paste = PasteFile.rsize(old_paste, w, h)

    return new_paste.url_i

@app.route('/d/<filehash>')
def download(filehash):
    paste_file = PasteFile.get_by_filehash(filehash)

    return send_file(open(paste_file.path, 'rb'),
                     mimetype='application/octet-stream',
                     cache_timeout=ONE_MONTH,
                     as_attachment=True,
                     attachment_filename=paste_file.filename.encode('utf-8'))

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        uploaded_file = request.files['file']
        w = request.form.get['w']
        h = request.form.get['h']
        if not uploaded_file:
            return abort(400)

        if w and h:
            paste_file = PasteFile.rsize(uploaded_file, w, h)
        else:
            parse_file = PasteFile.creat_by_upload_file(uploaded_file)
        db.session.add(parse_file)
        db.session.commit()

        return jsonify({
            'url_d': parse_file.url_d,
            'url_i': parse_file.url_i,
            'url_s': parse_file.url_s,
            'url_p': parse_file.url_p,
            'filename': parse_file.filename,
            'size': humanize_bytes(parse_file.size),
            'time': str(parse_file.uploadtime),
            'type': parse_file.type,
            'quoteurl': parse_file.quoteurl,
        })
    return render_template('index.html', **locals())


@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('j', methods=['POST'])
def j():
    uploaded_file = request.files['file']

    if uploaded_file:
        paste_file = PasteFile.creat_by_upload_file(uploaded_file)
        db.session.add(paste_file)
        db.session.commit()
        width, height = paste_file.image_size

        return jsonify({
            'url': paste_file.url_i,
            'short_url': paste_file.url_s,
            'origin_filename': paste_file.filename,
            'hash': paste_file.filehash,
            'width': width,
            'height': height,
        })

    return abort(400)

@app.route('/p/<filehash>')
def preview(filehash):
    paste_file = PasteFile.get_by_filehash(filehash)

    if not paste_file:
        filepath = get_file_path(filehash)
        if not(os.path.exist(filepath) and (not os.path.islink(filepath))):
            return abort(404)

        paste_file = PasteFile.creat_by_old_paste(filehash)
        db.session.add(paste_file)
        db.session.commit()

    return render_template('success.html', p=paste_file)

@app.route('/s/<symlink>')
def s(symlink):
    paste_file = PasteFile.get_by_symlink(symlink)

    return redirect(paste_file.url_p)

if __name__ == '__main__':
    app.run()
