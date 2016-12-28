import os
import time
import imgurpython
import requests
import sqlite3
import itertools
from collections import namedtuple
import json
import pdb


DIR_NAME_FRMT = 'cats-%s'
tags = ['cat', 'cats', 'lolcat', 'lolcats']
DB_FILE_NAME = 'cats2.db'

ImageData = namedtuple('ImageData', ['id', 'link', 'title', 'height', 'width'])
ImgurConfig = namedtuple('ImgurConfig', ['id', 'secret'])


def get_config(config_path='./config.json'):
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)        
    # Perhaps: return ImgurConfig(**config)
    return ImgurConfig(config['id'], config['secret'])


def init_db(table_name='cats'):
    db_connection = sqlite3.connect(DB_FILE_NAME)
    cursor = db_connection.cursor()
    cursor.execute('create table %s(image_id, date)' % (table_name,))
    db_connection.commit()
    cursor.close()
    db_connection.close()


def get_all_from__db(table_name='cats', db_file_name=DB_FILE_NAME):
    db_connection = sqlite3.connect(db_file_name)
    cursor = db_connection.cursor()
    cursor.execute('select * from %s' % (table_name,))
    db_connection.commit()
    cursor.close()
    db_connection.close()


def add_to_db(image_id, date, table_name='cats'):
    db_connection = sqlite3.connect(DB_FILE_NAME)
    cursor = db_connection.cursor()
    cursor.execute('insert into %s values (?, ?)' % (table_name,), (image_id, date))
    db_connection.commit()
    db_connection.close()


def add_bulk_to_db(image_iter, table_name='cats'):
    db_connection = sqlite3.connect(DB_FILE_NAME)
    cursor = db_connection.cursor()
    cursor.execute('insert into %s values (?, ?)' % (table_name,), image_iter)
    db_connection.commit()
    db_connection.close()


def does_image_exist(image_id, table_name='cats'):
    db_connection = sqlite3.connect(DB_FILE_NAME)
    try:
        cursor = db_connection.cursor()
        cursor.execute('select * from %s where image_id=?' % (table_name,), (image_id,))
        rows = cursor.fetchall()
        cursor.close()
        return len(rows) >= 1
    finally:
        db_connection.close()


def predicate(image):
    return True
    if image.height < 500 or image.width < 300:
        return False
    if image.height > 1200:
        return False
    return True


def get_todays_dir(dir_frmt=DIR_NAME_FRMT):
    return dir_frmt % (time.strftime('%Y-%m-%d'))


def remove_existing(images_data):
    print str(len(images_data)) + '!!!'
    nonexisiting_images = []
    for i in images_data:
        if not does_image_exist(i.id):
            nonexisiting_images.append(i)
    return nonexisiting_images

def flatten_items(items, client):
    for item in items:
        if item.is_album:
            album_images = client.get_album_images(item.id)
            for album_image in album_images:
                yield ImageData(album_image.id, album_image.link, item.title, album_image.height, album_image.width)
        elif type(item) is imgurpython.imgur.models.gallery_image.GalleryImage:
            yield ImageData(item.id, item.link, item.title, item.height, item.width)

def get_images_data_by_tag(imgur_config, tag, num=150, sort='viral'):
    client = imgurpython.ImgurClient(imgur_config.id, imgur_config.secret)
    images_by_tag = client.gallery_tag(tag, sort=sort)
    images_data = [i for i in flatten_items(images_by_tag.items, client) if predicate(i)]
    # return itertools.islice(images_data, num)
    print len(images_data), '???'
    # pdb.set_trace()
    return images_data[:num]


def get_images_of_tag(imgur_config, tag, num=150, sort='viral'):
    current_page = 1
    continue_download = True
    count_images = 0
    while continue_download:
        images_data = get_images_data_by_tag(imgur_config, tag, num, sort)

        new_images_data = remove_existing(images_data)
        print len(new_images_data)
        count_images += len(new_images_data)
        curr_date = time.strftime('%Y-%m-%d')

        for i in new_images_data:
            file_name = '%s\\%s.jpg'%(get_todays_dir(), i.id)
            try:
                print i.title
            except UnicodeEncodeError as e:
                print 'Could not print image name. ID ' + i.id
            with open(file_name,'wb') as f:
                f.write(requests.get(i.link).content)
                add_to_db(i.id, curr_date)
        current_page += 1
        if len(new_images_data) == 0 or count_images >= num:
            continue_download = False


def main():
    if not os.path.isfile(DB_FILE_NAME):
        init_db()

    cats_dir = get_todays_dir()
    if not os.path.isdir(cats_dir):
        os.makedirs(cats_dir)

    imgur_config = get_config()
    for tag in tags:
        print 'Downloading images for tag ' + tag
        get_images_of_tag(imgur_config, tag, sort='time')


if __name__ == '__main__':
    main()