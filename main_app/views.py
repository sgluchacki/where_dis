from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.views.generic import ListView
from .models import GameInstance, Photo
import uuid
import boto3
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import copy


# ----------------------CONSTANTS-------------------------- #


S3_BASE_URL = 'https://s3.us-east-2.amazonaws.com/'
BUCKET = 'laurens-cat-collector'


# -----------------------GENERAL--------------------------- #


def home(request):
    return render(request, 'home.html')


def signup(request):
  error_message = ''
  if request.method == 'POST':
    form = UserCreationForm(request.POST)
    if form.is_valid():
      user = form.save()
      login(request, user)
      return redirect('game_list')
    else:
      error_message = 'Something went wrong! :( Give it another shot'
  form = UserCreationForm()
  context = {'form': form, 'error_message': error_message}
  return render(request, 'registration/signup.html', context)


# ------------------------GAMES---------------------------- #

class GameList(ListView):
  model = GameInstance
  

# THIS IS THE BIG FUNCTION
# MAKE SURE WE SEND THE DATA WE NEED TO THE GAME DETAIL VIEW 
def game_detail(request, game_id):
  game_from_db = GameInstance.objects.get(id=game_id)
  return render(request, 'game/detail.html', {
    'game': game_from_db
  })

# def game_map(request):
#     mapbox_access_token = ''
#     return render(request, 'map.html', { 'mapbox_access_token': mapbox_access_token })

def game_map(request, game_id):
  # NEED TO PASS CENTER OF MAP DATA HERE
  context = {'mapbox_access_token': ''}
  
  return redirect('game_detail', context, game_id=game_id)



# ------------------------PHOTOS---------------------------- #
def get_decimal_coordinates(info):
  for key in ['Latitude', 'Longitude']:
      if 'GPS'+key in info and 'GPS'+key+'Ref' in info:
          e = info['GPS'+key]
          ref = info['GPS'+key+'Ref']
          info[key] = ( e[0][0]/e[0][1] +
                        e[1][0]/e[1][1] / 60 +
                        e[2][0]/e[2][1] / 3600
                      ) * (-1 if ref in ['S','W'] else 1)

  if 'Latitude' in info and 'Longitude' in info:
      return [info['Latitude'], info['Longitude']]

def upload_photo(request, game_id): # DOUBLE-CHECK GAME ID AND MULTIPLE KWARGS
  photo_file = request.FILES.get('photo-file', None)
  photo_copy = copy.deepcopy(photo_file)
  exif = Image.open(photo_copy)._getexif()
  print(exif is not None)
  if exif is not None:
      for key, value in exif.items():
          name = TAGS.get(key, key)
          exif[name] = exif.pop(key)

      if 'GPSInfo' in exif:
          for key in exif['GPSInfo'].keys():
              name = GPSTAGS.get(key,key)
              exif['GPSInfo'][name] = exif['GPSInfo'].pop(key)
              
  print(exif, 'EXIFFFFFFFF')
  decimals = get_decimal_coordinates(exif['GPSInfo'])
  print(decimals)
  
  if photo_file:
    s3 = boto3.client('s3')
    key = uuid.uuid4().hex[:6] + photo_file.name[photo_file.name.rfind('.'):]
    
    try:
      print('TRY step 1')
      s3.upload_fileobj(photo_file, BUCKET, key)
      print('TRY step 2')
      url = f'{S3_BASE_URL}{BUCKET}/{key}'
      print(f'TRY step 3 url = {url}')
      photo = Photo(url=url, game_instance_id=game_id, user=request.user) # DOUBLE-CHECK HERE TOO
      print(f'TRY step 4 photo = {photo}')
      photo.save()
      print('TRY step 5')
    except:
      print('There has been an error uploading to S3')
  return redirect('game_detail', game_id=game_id)