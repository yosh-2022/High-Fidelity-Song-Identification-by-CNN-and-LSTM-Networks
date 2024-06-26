# -*- coding: utf-8 -*-


!git clone https://github.com/marl/crepe.git

# Commented out IPython magic to ensure Python compatibility.
# %cd crepe

# Commented out IPython magic to ensure Python compatibility.
# %ls

!cat requirements.txt

!pip install -r requirements.txt

!python setup.py

import crepe
import numpy as np
from scipy.io import wavfile
import pandas as pd
import tensorflow as tf
import random
tf.test.gpu_device_name()
import matplotlib.pyplot as plt
from google.colab import drive
drive.mount('/content/drive')

!pip install -U -q PyDrive
 
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from google.colab import auth
from oauth2client.client import GoogleCredentials
 
auth.authenticate_user()
gauth = GoogleAuth()
gauth.credentials = GoogleCredentials.get_application_default()
drive = GoogleDrive(gauth)

!pip install --upgrade --user hmmlearn

# Commented out IPython magic to ensure Python compatibility.
# %ls

# MILESTONE 2 CODE

# read in files from drive folder
wav_list = drive.ListFile({'q': "'1KpvZoqdA20QqI1hpzBf-StrE46Mw00g7' in parents and trashed=false"}).GetList()
count_wav = 0
for file in wav_list:
  count_wav += 1
print("Number of wav: ", count_wav)

# get the .wav titles from files in drive folder

filter_wav_list = []
for wav in wav_list:
  filter_wav_list.append(wav['title'])
print(filter_wav_list)

# Commented out IPython magic to ensure Python compatibility.
# %cd ..
# %cd drive/My Drive/Final Project/Training_Dataset_1/

# %ls

# simple algorithm to calculate pitch from a given frequency

from math import log2, pow

A4 = 440

C0 = A4*pow(2, -4.75)

pitch_name = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

def pitch(freq):

 h = round(12*log2(freq/C0))

 octave = h // 12

 n = h % 12

 return pitch_name[n]    #name[n] + str(octave)

# read in a wav file, and run crepe to get the list of frequencies, 1 freq per 10 ms
def readWav(wavName):
  to_read = wavName + '.wav'

  sr, audio = wavfile.read(to_read)
  time, frequency, confidence, activation = crepe.predict(audio, sr, viterbi = True)

  return frequency

# convert frequency list into list of pitches
def freq_to_pitches(frequency):
  compressed_frequencies = []
  compressed_frequencies.append(frequency[0])
  index = 0
  count = 0

  # to normalize small deviations in the frequency read 
  for freq in frequency:
    if abs(freq - compressed_frequencies[index]) < (12 * log2(freq/C0)) and count < 5:
      count += 1
      continue
    else:
      compressed_frequencies.append(freq)
      index += 1
      count = 0

  pitches = []
  count = 0
  for freq in compressed_frequencies:
    note = pitch(freq)
    # get rid of white noise from the first 0.5s of music
    if "1" in note and count < 50:
      count 
      continue
    else:
      pitches.append(note)

  np_pitches = np.array(pitches)

  return np_pitches

# main code to read wav file --> pitch list
training_dict_pred = {}
for wav in filter_wav_list:
  if '.wav' in wav:
    wavName = wav.split('.')[0]
    pred_freq = readWav(wavName)
    training_dict_pred[wavName] = freq_to_pitches(pred_freq)

print(training_dict_pred)

# dictionaries for pitch-index and song title-index mappings
pitch_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
ix_to_pitch = {i:pitch for i, pitch in enumerate(pitch_names)}
pitch_to_ix = {pitch:i for i, pitch in enumerate(pitch_names)}
titles = []

for title, notes in training_dict_pred.items():
  titles.append(title)

ix_to_title = {i:title for i, title in enumerate(titles)}
title_to_ix = {title:i for i, title in enumerate(titles)}

# convert each song's array into indices

# Generate training data
training_dict_pred_nums = {}

for title, notes in training_dict_pred.items():
  training_dict_pred_nums[title] = []
  nums = []
  # training set data augmentation -- split the song into 5 second intervals
  for i in range(len(notes)):
    nums.append(pitch_to_ix[notes[i]])
    if i % 100 == 0 and i > 0:
      training_dict_pred_nums[title].append(np.asarray(nums))
      nums = []

# Generate validation set
validate_dict_pred_nums = {}

# shift the 5-second interval to create validation set
for title, notes in training_dict_pred.items():
  validate_dict_pred_nums[title] = []
  nums = []
  shift = 0
  for i in range(len(notes)):
    if shift < 30:
      shift += 1
      continue
    else: 
      nums.append(pitch_to_ix[notes[i]])
      if i % 100 == 0 and i > 0:
        validate_dict_pred_nums[title].append(np.asarray(nums))
        nums = []

# Generate test set via data augmentation
test_dict_pred_nums = {}
random.seed(1)
for title, notes in training_dict_pred.items():
  test_dict_pred_nums[title] = []
  nums = []

  # test set data augmentation -- split the song into 4 second intervals
  # don't need all the slices, only retaining 10%
  for i in range(len(notes)):
    nums.append(pitch_to_ix[notes[i]])
    rand_num = random.random()
    if i % 40 == 0 and i > 0 and rand_num < 0.1:
      test_dict_pred_nums[title].append(np.asarray(nums))
      nums = []

# build RNN model 
from keras import Sequential
from keras.layers import Embedding, LSTM, Dense, Dropout
from keras.preprocessing import sequence

# padding
max_length = 100  # 10 second increments
X_train = []
Y_train = []
for title, nums in training_dict_pred_nums.items():
  nums = sequence.pad_sequences(nums, maxlen=max_length, padding='post')
  for num in nums:
    X_train.append(np.asarray(num))
    # create one-hot vector for Y
    Y = np.zeros(10)  
    Y[title_to_ix[title]] = 1
    Y_train.append(Y)
X_train = np.asarray(X_train)
Y_train = np.asarray(Y_train)

X_valid = []
Y_valid = []
for title, nums in validate_dict_pred_nums.items():
  nums = sequence.pad_sequences(nums, maxlen=max_length, padding='post')
  for num in nums:
      X_valid.append(np.asarray(num))
      Y = np.zeros(10)
      Y[title_to_ix[title]] = 1
      Y_valid.append(Y)
X_valid = np.asarray(X_valid)
Y_valid = np.asarray(Y_valid)

X_test = []
Y_test = []
for title, nums in test_dict_pred_nums.items():
  nums = sequence.pad_sequences(nums, maxlen=max_length, padding='post')
  for num in nums:
    X_test.append(np.asarray(num))
    Y = np.zeros(10)
    Y[title_to_ix[title]] = 1
    Y_test.append(Y)
X_test = np.asarray(X_test)
Y_test = np.asarray(Y_test)

# model 
embedding_size = 32

model=Sequential()
model.add(Embedding(12, embedding_size, input_length=max_length))
model.add(LSTM(300, stateful = False))
model.add(Dropout(0.5))
model.add(Dense(300, activation="relu"))
model.add(Dropout(0.5))
model.add(Dense(300, activation="relu"))
model.add(Dropout(0.5))
model.add(Dense(10, activation='softmax'))
print(model.summary())

model.compile(loss='binary_crossentropy', 
             optimizer='adam', 
             metrics=['accuracy'])

num_epochs = 150
history = model.fit(X_train, Y_train, validation_data=(X_valid, Y_valid), epochs=num_epochs)

test_result = model.evaluate(x=X_test, y=Y_test)
dict(zip(model.metrics_names, test_result))

# Commented out IPython magic to ensure Python compatibility.
# TEST 2 -- real recorded data for one song (Beyonce Halo)
# %cd ../Another_Test
# %ls

# read in files from drive folder
test2_wav_list = drive.ListFile({'q': "'1b-XyppeZa1jMxfewjXOjaxyAMnB3Jraj' in parents and trashed=false"}).GetList()
count_wav = 0
for file in test2_wav_list:
  count_wav += 1
print("Number of wav: ", count_wav)

# get the .wav titles from files in drive folder
filter_test2_wav_list = []
for wav in test2_wav_list:
  filter_test2_wav_list.append(wav['title'])
print(filter_test2_wav_list)

# get pitch list for self-generated test data
test2_dict_pred = {}
for wav in filter_test2_wav_list:
  if '.wav' in wav:
    wavName = wav.split('.')[0]
    pred_freq = readWav(wavName)
    test2_dict_pred[wavName] = freq_to_pitches(pred_freq)

# convert data into keras-model accepted format

test2_dict_pred_nums = {}
for title, notes in test2_dict_pred.items():
  test2_dict_pred_nums[title] = []
  nums = []
  for i in range(len(notes)):
    nums.append(pitch_to_ix[notes[i]])
    if i % 100 == 0 and i > 0:
      test2_dict_pred_nums[title].append(np.asarray(nums))
      nums = []

# data pad + more configurations
X_test2 = []
Y_test2 = []
max_length = 100
for title, nums in test2_dict_pred_nums.items():
  nums = sequence.pad_sequences(nums, maxlen=max_length, padding='post')
  for num in nums:
    X_test2.append(np.asarray(num))
    Y = np.zeros(10)
    Y[title_to_ix[title]] = 1
    Y_test2.append(Y)
X_test2 = np.asarray(X_test2)
Y_test2 = np.asarray(Y_test2)
print(X_test2.shape)
print(Y_test2.shape)

test_result = model.evaluate(x=X_test2, y=Y_test2)
dict(zip(model.metrics_names, test_result))

predictions = model.predict_classes(X_test2)
print(predictions)
print(ix_to_title[9])

# Commented out IPython magic to ensure Python compatibility.
# TEST 3 -- more real recorded data (many songs)
# %cd ../Test_Set
# %ls

# read in files from drive folder
test3_wav_list = drive.ListFile({'q': "'163E5MPniUSSCuQiA4Ys4oUCWqSGtinob' in parents and trashed=false"}).GetList()
count_wav = 0
for file in test3_wav_list:
  count_wav += 1
print("Number of wav: ", count_wav)

# get the .wav titles from files in drive folder
filter_test3_wav_list = []
for wav in test3_wav_list:
  filter_test3_wav_list.append(wav['title'])
print(filter_test3_wav_list)

# get pitch list for self-generated test data
test3_dict_pred = {}
for wav in filter_test3_wav_list:
  if '.wav' in wav:
    wavName = wav.split('.')[0]
    pred_freq = readWav(wavName)
    test3_dict_pred[wavName] = freq_to_pitches(pred_freq)

# convert data into keras-model accepted format
test3_dict_pred_nums = {}
for title, notes in test3_dict_pred.items():
  test3_dict_pred_nums[title] = []
  nums = []
  for i in range(len(notes)):
    nums.append(pitch_to_ix[notes[i]])
    if i % 100 == 0 and i > 0:
      test3_dict_pred_nums[title].append(np.asarray(nums))
      nums = []

X_test3 = []
Y_test3 = []
max_length = 100
for title, nums in test3_dict_pred_nums.items():
  nums = sequence.pad_sequences(nums, maxlen=max_length, padding='post')
  for num in nums:
    X_test3.append(np.asarray(num))
    # create one-hot vectors for the corresponding song titles
    Y = np.zeros(10)
    Y[title_to_ix[title]] = 1
    Y_test3.append(Y)
X_test3 = np.asarray(X_test3)
Y_test3 = np.asarray(Y_test3)
print(X_test3.shape)
print(Y_test3.shape)

test_result = model.evaluate(x=X_test3, y=Y_test3)
dict(zip(model.metrics_names, test_result))

accuracy = history.history['accuracy']
print(accuracy)
plt.plot(accuracy)
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.title('RNN Model Training Accuracy')
plt.show()

# FOR MILESTONE 1
csv_list = drive.ListFile({'q': "'1FLPDEbQMm1wyC0YN1qqJE-Tr_QfmEZsa' in parents and trashed=false"}).GetList()
wav_list = drive.ListFile({'q': "'1R9oj_px1gHIkJ2aJxkdDMuWAlcNF3qmm' in parents and trashed=false"}).GetList()
count_csv = 0
count_wav = 0
for file in csv_list:
  count_csv += 1
for file in wav_list:
  count_wav += 1
print("Number of files: ", count_csv)
print("Number of wav: ", count_wav)

# FOR MILESTONE 1
def getTrueFreq(wavName):
  true_labels = []
  for file in csv_list:
    if file['title'] == wavName + '.csv':
      #downloaded = drive.CreateFile({'id':file['id']})
      file.GetContentFile(file['title'])
      true_labels = pd.read_csv(file['title'], delimiter='\t', usecols=[0 ,1])
  
  if len(true_labels) == 0:
    return None

  true_labels = true_labels.to_numpy()
  np.set_printoptions(threshold=np.inf)

  true_freq = []
  for label in true_labels:
    true_freq.append(label[1])
  true_freq = np.array(true_freq)
  return true_freq

# FOR MILESTONE 1
name = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

def error_check(frequency, true_labels, errors):
  error = 0
  iter_range = min(frequency.size, true_labels.size)

  for i in range(iter_range):
    if true_labels[i] == 0:
      continue
    else:
      true_pitch = pitch(true_labels[i])
      est_pitch = pitch(frequency[i])
      if abs(name.index(true_pitch) - name.index(est_pitch)) > 1:
        error += 1
  
  return error / len(true_labels)

# FOR MILESTONE 1
def remove_excess_csv():
  for file in wav_list:
    if '.csv' in file['title']:
      file.Delete()

# FOR MILESTONE 1
errors = []
count = 0
for wav in wav_list:
  if '.wav' in wav['title']:
    wavName = wav['title'].split('.')[0]
    true_freq = getTrueFreq(wavName)
    pred_freq = readWav(wavName)

    if len(true_freq) > 0:
      cur_error_rate = error_check(pred_freq, true_freq, errors)
      errors.append(cur_error_rate)
      count += 1
    if count == 20:
      cur_avg_error = np.array(errors)
      print("Current error rate: ", np.average(cur_avg_error))
      count = 0

overall_errors = np.array(errors)
print("Overall error rate: ", np.average(overall_errors))

# FOR MILESTONE 1
remove_excess_csv()

# FOR MILESTONE 1
plt.plot(overall_errors)
plt.xlabel('Wav Song Number')
plt.ylabel('Error Rate')
plt.title('Error Rate of CREPE over test set')
plt.show()
