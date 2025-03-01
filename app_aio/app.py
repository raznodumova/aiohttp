from aiohttp import web
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from database import get_db, Base, engine
from models import User, Adventure
from werkzeug.security import generate_password_hash, check_password_hash
from base64 import b64decode
from functools import wraps

async def init_db(app):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

def basic_auth_required(handler):
    @wraps(handler)
    async def middleware(request):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Basic '):
            return web.json_response({'message': 'Unauthorized'}, status=401)

        auth_decoded = b64decode(auth_header[6:]).decode('utf-8')
        email, password = auth_decoded.split(':', 1)

        async with get_db() as session:
            result = await session.execute(select(User).filter_by(email=email))
            user = result.scalars().first()
            if not user or not user.verify_password(password):
                return web.json_response({'message': 'Unauthorized'}, status=401)

        request['user'] = user
        return await handler(request)
    return middleware

async def register_user(request):
    data = await request.json()
    if not data or 'email' not in data or 'password' not in data:
        return web.json_response({'message': 'Bad request'}, status=400)

    async with get_db() as session:
        result = await session.execute(select(User).filter_by(email=data['email']))
        if result.scalars().first():
            return web.json_response({'message': 'Email in use'}, status=400)

        user = User(email=data['email'], password=generate_password_hash(data['password']))
        session.add(user)
        await session.commit()
        return web.json_response({'message': 'OK'}, status=201)

@basic_auth_required
async def create_ads(request):
    data = await request.json()
    if not data or 'title' not in data or 'description' not in data:
        return web.json_response({'message': 'Bad request'}, status=400)

    user = request['user']
    async with get_db() as session:
        new_ads = Adventure(title=data['title'], description=data['description'], owner=user)
        session.add(new_ads)
        await session.commit()
        return web.json_response({
            'id': new_ads.id,
            'title': new_ads.title,
            'description': new_ads.description,
            'owner': new_ads.owner.email}, status=201)

async def get_ads(request):
    async with get_db() as session:
        result = await session.execute(select(Adventure).options(selectinload(Adventure.owner)))
        ads = result.scalars().all()
        return web.json_response([{
            'id': ad.id,
            'title': ad.title,
            'description': ad.description,
            'owner': ad.owner.email} for ad in ads])

async def get_ads_by_id(request):
    ads_id = int(request.match_info['ads_id'])
    async with get_db() as session:
        result = await session.execute(select(Adventure).filter_by(id=ads_id).options(selectinload(Adventure.owner)))
        ads = result.scalars().first()
        if not ads:
            return web.json_response({'message': 'Not found'}, status=404)
        return web.json_response({
            'id': ads.id,
            'title': ads.title,
            'description': ads.description,
            'owner': ads.owner.email})

@basic_auth_required
async def delete_ads(request):
    ads_id = int(request.match_info['ads_id'])
    user = request['user']
    async with get_db() as session:
        result = await session.execute(select(Adventure).filter_by(id=ads_id).options(selectinload(Adventure.owner)))
        ads = result.scalars().first()
        if not ads:
            return web.json_response({'message': 'Not found'}, status=404)
        if ads.owner != user:
            return web.json_response({'message': 'Forbidden'}, status=403)
        await session.delete(ads)
        await session.commit()
        return web.json_response({'message': 'OK'})

@basic_auth_required
async def update_ads(request):
    ads_id = int(request.match_info['id'])
    data = await request.json()
    user = request['user']
    async with get_db() as session:
        result = await session.execute(select(Adventure).filter_by(id=ads_id).options(selectinload(Adventure.owner)))
        ads = result.scalars().first()
        if not ads:
            return web.json_response({'message': 'Not found'}, status=404)
        if ads.owner != user:
            return web.json_response({'message': 'Forbidden'}, status=403)
        if 'title' in data:
            ads.title = data['title']
        if 'description' in data:
            ads.description = data['description']
        await session.commit()
        return web.json_response({
            'id': ads.id,
            'title': ads.title,
            'description': ads.description,
            'owner': ads.owner.email})

app = web.Application()
app.on_startup.append(init_db)
app.router.add_post('/register', register_user)
app.router.add_post('/new', create_ads)
app.router.add_get('/ads', get_ads)
app.router.add_get('/ads/{ads_id}', get_ads_by_id)
app.router.add_delete('/delete/{ads_id}', delete_ads)
app.router.add_put('/update/{id}', update_ads)

if __name__ == '__main__':
    web.run_app(app, port=8080)