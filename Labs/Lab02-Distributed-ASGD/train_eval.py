import os
import re
import sys
import time
from datetime import datetime
import json

import tensorflow as tf


from tensorflow.python.keras import regularizers
from tensorflow.python.keras.estimator import model_to_estimator
from tensorflow.python.keras.optimizers import Adadelta, Adam, RMSprop


FLAGS = tf.app.flags.FLAGS

# Default global parameters
tf.app.flags.DEFINE_integer('batch_size', 32, "Number of images per batch")
tf.app.flags.DEFINE_integer('max_steps', 100000, "Number of steps to train")
tf.app.flags.DEFINE_string('job_dir', '../../jobdir/run1', "Checkpoints")
tf.app.flags.DEFINE_string('data_dir', '../../data/tiny-imagenet', "Data")
tf.app.flags.DEFINE_float('lr', 0.0005, 'Learning rate')
tf.app.flags.DEFINE_string('verbosity', 'INFO', "Control logging level")
tf.app.flags.DEFINE_integer('num_parallel_calls', 12, 'Input parallelization')
tf.app.flags.DEFINE_integer('throttle_secs', 300, "Evaluate every n seconds")


from resnet import network_model
from feed import INPUT_NAME, IMAGE_SHAPE, NUM_CLASSES, input_fn, serving_input_fn


def train_evaluate():

  #Create a keras model
  model = network_model(IMAGE_SHAPE, INPUT_NAME, NUM_CLASSES)
  loss = 'sparse_categorical_crossentropy'
  metrics = ['accuracy']
  opt = Adadelta()
  model.compile(loss=loss, optimizer=opt, metrics=metrics)

  #Convert the the keras model to tf estimator
  estimator = model_to_estimator(keras_model = model, model_dir=FLAGS.job_dir)
    
  #Create training, evaluation, and serving input functions
  train_input_fn = lambda: input_fn(data_dir=FLAGS.data_dir, 
                                    is_training=True, 
                                    batch_size=FLAGS.batch_size, 
                                    num_parallel_calls=FLAGS.num_parallel_calls)
    
  valid_input_fn = lambda: input_fn(data_dir=FLAGS.data_dir, 
                                    is_training=False, 
                                    batch_size=FLAGS.batch_size, 
                                    num_parallel_calls=FLAGS.num_parallel_calls)
  
  #Create training and validation specifications
  train_spec = tf.estimator.TrainSpec(input_fn=train_input_fn, 
                                      max_steps=FLAGS.max_steps)
  
  export_latest = tf.estimator.FinalExporter("classifier", serving_input_fn)
    
  eval_spec = tf.estimator.EvalSpec(input_fn=valid_input_fn, 
                                    steps=None,
                                    throttle_secs=FLAGS.throttle_secs,
                                    exporters=export_latest)
  
 
  #Start training
  tf.logging.set_verbosity(FLAGS.verbosity)
  tf.estimator.train_and_evaluate(estimator, train_spec, eval_spec)
  
  

# Azure Batch AI does not properly set TF_CONFIG environment variable
# as required by  train_and_evaluate function in the current versions of TF.
# As a temporary hack we fix in the below function
# 
def fix_tf_config():
    
  if 'TF_CONFIG' not in os.environ:
    return

  tf_config = json.loads(os.environ['TF_CONFIG'])
  cluster = tf_config['cluster']
  task = tf_config['task']
  worker = cluster['worker']
  chief = {"chief": [worker.pop(0)]} 
  cluster.update(chief)
  if task['type'] == 'master':
    task['type']='chief'
  elif task['type'] == 'worker':
    task['index'] = task['index'] - 1
  tf_config = {'cluster': cluster, 'task': task}
  os.environ['TF_CONFIG'] = json.dumps(tf_config)

    

def main(argv=None):
 
  if tf.gfile.Exists(FLAGS.job_dir):
    tf.gfile.DeleteRecursively(FLAGS.job_dir)
  tf.gfile.MakeDirs(FLAGS.job_dir)
  
  fix_tf_config()

  train_evaluate()
  

if __name__ == '__main__':
  tf.app.run()
  
  
    
    
