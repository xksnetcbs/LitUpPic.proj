from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from datetime import datetime
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:tianjin3000@localhost:3306/lituppic'
CORS(app)
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")


# 定义数据库模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    activated = db.Column(db.Boolean, default=False)


class Tile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    row = db.Column(db.Integer, nullable=False)
    col = db.Column(db.Integer, nullable=False)
    lit = db.Column(db.Boolean, default=False)
    lit_at = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('tiles', lazy=True))


# 创建数据库表
# @app.before_first_request
# def create_tables():
#     db.create_all()
#
#     # 初始化方块数据 (8x8网格)
#     if Tile.query.count() == 0:
#         for row in range(1, 9):
#             for col in range(1, 9):
#                 tile = Tile(row=row, col=col)
#                 db.session.add(tile)
#         db.session.commit()


# API端点
@app.route('/api/activate', methods=['POST'])
def activate_user():
    data = request.get_json()
    username = data.get('username')

    if not username:
        return jsonify({'error': 'Username is required'}), 400

    # 检查用户名是否已存在
    # user = User.query.filter_by(username=username).first()
    # if user:
    #     return jsonify({'error': 'Username already exists'}), 400

    # 将用户设置为点亮

    users = User.query.all()
    activated = False
    for user in users:
        if user.username == username:
            # if user.activated:
            #     return jsonify({'error': 'User already activated'}), 400
            user.activated = True
            activated = True

    # new_user = User(username=username)
            db.session.add(user)
    db.session.commit()
    if activated:
        return jsonify({
            'message': 'User activated',
            'user_id': User.query.filter_by(username=username).first().id
        })
    else:
        return jsonify({'error': 'User not found'}), 404


@app.route('/api/tiles', methods=['GET'])
def get_tiles():
    tiles = Tile.query.all()
    tiles_data = [{
        'id': tile.id,
        'row': tile.row,
        'col': tile.col,
        'lit': tile.lit,
        'lit_at': tile.lit_at.isoformat() if tile.lit_at else None,
        'user': tile.user.username if tile.user else None
    } for tile in tiles]

    return jsonify(tiles_data)

@app.route('/api/users', methods=['GET'])
def get_users():
    users = User.query.filter_by(activated=True)
    users_data = [{
        'id': user.id,
        'username': user.username,
        'created_at': user.created_at.isoformat(),
        'activated': user.activated
    } for user in users]

    return jsonify(users_data)

@app.route('/api/light_tile', methods=['POST'])
def light_tile():
    data = request.get_json()
    tile_id = data.get('tile_id')
    user_id = data.get('user_id')

    tile = Tile.query.get(tile_id)
    user = User.query.get(user_id)

    if not tile or not user:
        return jsonify({'error': 'Invalid tile or user'}), 400

    if tile.lit:
        return jsonify({'error': 'Tile already lit'}), 400

    # 点亮方块
    tile.lit = True
    tile.lit_at = datetime.utcnow()
    tile.user_id = user.id
    db.session.commit()

    # 广播更新
    tile_data = {
        'id': tile.id,
        'row': tile.row,
        'col': tile.col,
        'lit': tile.lit,
        'lit_at': tile.lit_at.isoformat(),
        'user': user.username
    }
    socketio.emit('tile_updated', tile_data)

    return jsonify({'message': 'Tile lit successfully'})

current_connections = 0

# WebSocket事件
@socketio.on('connect')
def handle_connect():
    global current_connections
    current_connections += 1
    print('Client connected', current_connections)



@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')
    global current_connections
    current_connections -= 1


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)