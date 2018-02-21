import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
import matplotlib.dates as mdates
import numpy as np
from scipy import signal
from scipy.fftpack import fft, ifft
from keras.models import Sequential
from keras.layers.core import Dense, Activation, Dropout
from keras.layers import LSTM
import time
from keras.callbacks import ModelCheckpoint
import os

import matplotlib.pyplot as plt

# plot original series
dir_path = os.getcwd()
data_dir = os.path.abspath(os.path.join(dir_path, '../data'))
combined_pkl = os.path.join(data_dir, 'combine.pkl')
part1_pkl = os.path.join(data_dir, "Part1.pkl")
part2_pkl = os.path.join(data_dir, "Part2.pkl")
file1 = os.path.join(data_dir,"Hackathon_DataSet_OctApr_Part1.txt")
file2 = os.path.join(data_dir,"Hackathon_DataSet_OctApr_Part2.txt")

#file1_df = pd.read_table(file1, sep='\t', header=0, parse_dates=['TimeStamp'], index_col=["Id"])
#file2_df = pd.read_table(file2, sep='\t', header=0, parse_dates=['TimeStamp'], index_col=["Id"])

#print(len(file1_df.columns))
#print(len(file2_df.columns))
#print(file1_df.columns)
#print(file2_df.columns)

#file_df = pd.merge(file1_df, file2_df, on="TimeStamp")
#file_df.to_pickle(combined_pkl)
file_df = pd.read_pickle(combined_pkl)

#file_df.info()


class anomaly_detection:
    def __enter__(self):
        return (self)

    def __init__(self, sequence_length=50, batch_size=64, epochs=50, dropout = 0.2):
        self.sequence_length = sequence_length
        self.batch_size = batch_size
        self.epochs = epochs
        self.dir_path = os.getcwd()
        self.data_dir = os.path.abspath(os.path.join(dir_path, '../data'))
        self.best_weights = os.path.join(data_dir, 'weights.hdf5')
        self.dropout = dropout

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def create_model(self, input_shape):

        #create model
        model = Sequential()
        layers = {'input': 1, 'hidden1': 64, 'hidden2': 512, 'hidden3': 256, 'hidden4': 100, 'output': 1}

        model.add(LSTM( input_shape=input_shape, units=layers['hidden1'], return_sequences=True))
        model.add(Dropout(self.dropout))

        model.add(LSTM(units=layers['hidden2'],return_sequences=True))
        model.add(Dropout(self.dropout))

        model.add(LSTM(units=layers['hidden3'], return_sequences=True))
        model.add(Dropout(self.dropout))

        model.add(LSTM(units=layers['hidden4'], return_sequences=False))
        model.add(Dropout(self.dropout))

        model.add(Dense(units=layers['output']))
        model.add(Activation("linear"))
        self.model = model
        self.model.compile(loss="mse", optimizer="rmsprop")

    def window_transform_series(self, series, window_size):
        # containers for input/output pairs
        X = []
        y = []
        # y values starts from index window_size till end
        y = series[window_size:]
        # x values ends windows_size before the end
        X = [series[:-window_size]]
        # Create window_size columns of shiffted x values
        for i in range(1, window_size):
            X = np.vstack((X, series[i:(i - window_size)]))
        # Transpose to rows
        X = X.T
        # reshape each
        X = np.asarray(X)
        X.shape = (np.shape(X)[0:2])
        y = np.asarray(y)
        y.shape = (len(y), 1)

        return X, y

    def process_timeseries(self, time_series):
        self.time_series = time_series
        self.time_values = range(len(time_series))
        X, y = self.window_transform_series(time_series, self.sequence_length)

        # split our dataset into training / testing sets
        train_test_split = int(np.ceil(2 * len(y) / float(3)))  # set the split point

        # partition the training set
        X_train = X[:train_test_split, :]
        y_train = y[:train_test_split]
        input_shape = (None, 1)
        self.create_model(input_shape)

        # keep the last chunk for testing
        X_test = X[train_test_split:, :]
        y_test = y[train_test_split:]

        # NOTE: to use keras's RNN LSTM module our input must be reshaped to [samples, window size, stepsize]
        X_train = np.asarray(np.reshape(X_train, (X_train.shape[0], self.sequence_length, 1)))
        X_test = np.asarray(np.reshape(X_test, (X_test.shape[0], self.sequence_length, 1)))

        checkpointer = ModelCheckpoint(filepath=self.best_weights, verbose=1,save_best_only=True)
        # run your model!
        history = self.model.fit(X_train, y_train, epochs=self.epochs, batch_size=self.batch_size, validation_data=(X_test, y_test), verbose=2,
                            shuffle=False, callbacks=[checkpointer])

        # load the weights that yielded the best validation accuracy
        self.model.load_weights(self.best_weights)
        # plot history
        plt.plot(history.history['loss'], label='train')
        plt.plot(history.history['val_loss'], label='test')
        plt.legend()
        plt.show()
        # generate predictions for training
        train_predict = self.model.predict(X_train)
        test_predict = self.model.predict(X_test)

        plt.plot(self.time_values, time_series, color='k')

        split_pt = train_test_split + self.sequence_length
        plt.plot(np.arange(self.sequence_length, split_pt, 1), train_predict, color='b')

        # plot testing set prediction
        plt.plot(np.arange(split_pt, split_pt + len(test_predict), 1), test_predict, color='r')

        # pretty up graph
        plt.xlabel('time ')
        plt.ylabel('21-LT-10516.PV_Prod_Sep_Oil_Interface_Level (%)')
        plt.legend(['original series', 'training fit', 'testing fit'])
        plt.show()


with anomaly_detection(sequence_length=50, batch_size=64, epochs=50, dropout=0.5) as anomaly_detection:
    start = time.time()
    start_time = datetime(2017, 3, 11,11,0)
    end_time = datetime(2017, 3, 12, 12,0)
    time_range= (file_df["TimeStamp"] < end_time) & (file_df["TimeStamp"] > start_time)
    time_series = file_df[time_range]["21-LT-10516.PV_Prod_Sep_Oil_Interface_Level (%)"]
    anomaly_detection.process_timeseries(time_series)