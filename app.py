from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, TextAreaField, DateTimeField, SubmitField
from wtforms.validators import DataRequired
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key'  # 適当なキーに変更
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///worklog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ---------- DB モデル ----------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)  # 実運用ならハッシュ化必須！

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    cleaned = db.Column(db.Boolean, default=False)
    flow = db.Column(db.String(10))
    comment = db.Column(db.String(200))
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='posts')

# ---------- フォーム ----------
class LoginForm(FlaskForm):
    username = StringField('ユーザー名', validators=[DataRequired()])
    password = PasswordField('パスワード', validators=[DataRequired()])
    submit = SubmitField('ログイン')

class PostForm(FlaskForm):
    cleaned = BooleanField('取水口清掃済')
    flow = SelectField('流量', choices=[('多い', '多い'), ('少ない', '少ない'), ('無し', '無し')])
    comment = TextAreaField('コメント')
    start_time = DateTimeField('開始日時', default=datetime.utcnow, format='%Y-%m-%d %H:%M:%S')
    submit = SubmitField('投稿')

# ---------- ログイン管理 ----------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------- ルート ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data, password=form.password.data).first()
        if user:
            login_user(user)
            return redirect(url_for('index'))
        flash('ログイン失敗')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(
            user_id=current_user.id,
            cleaned=form.cleaned.data,
            flow=form.flow.data,
            comment=form.comment.data,
            start_time=form.start_time.data
        )
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('index'))

    posts = Post.query.order_by(Post.start_time.desc()).all()
    return render_template('index.html', form=form, posts=posts)

@app.route('/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit(post_id):
    post = Post.query.get_or_404(post_id)
    if post.user_id != current_user.id:
        flash('自分の投稿しか編集できません')
        return redirect(url_for('index'))
    form = PostForm(obj=post)
    if form.validate_on_submit():
        post.cleaned = form.cleaned.data
        post.flow = form.flow.data
        post.comment = form.comment.data
        post.start_time = form.start_time.data
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit.html', form=form)

@app.route('/delete/<int:post_id>')
@login_required
def delete(post_id):
    post = Post.query.get_or_404(post_id)
    if post.user_id == current_user.id:
        db.session.delete(post)
        db.session.commit()
    return redirect(url_for('index'))

# ---------- 初回起動時にDB作成 ----------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.first():
            users = [
                User(username='user1', password='pass1'),
                User(username='user2', password='pass2'),
                User(username='user3', password='pass3'),
                User(username='user4', password='pass4'),
                User(username='user5', password='pass5'),
            ]
            db.session.add_all(users)
            db.session.commit()
    app.run(host="0.0.0.0", port=5000, debug=True)

# 投稿フォーム専用ページ
@app.route("/new", methods=["GET", "POST"])
@login_required
def new():
    form = PostForm()
    if form.validate_on_submit():
        entry = WorkEntry(
            user_id=current_user.id,
            cleaned=form.cleaned.data,
            flow=form.flow.data,
            comment=form.comment.data,
            start_time=form.start_time.data,
        )
        db.session.add(entry)
        db.session.commit()
        flash("投稿を保存しました")
        return redirect(url_for("index"))
    return render_template("new.html", form=form)
