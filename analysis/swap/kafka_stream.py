import swap

from kafka.client import KafkaClient
from kafka.consumer import SimpleConsumer
import os,sys,datetime
import json
import base64

class kafka_stream(object):
  
  def __init__(self):
    self.kafka         = KafkaClient("ec2-23-22-205-190.compute-1.amazonaws.com", 9092)
    self.consumer      = SimpleConsumer(self.kafka, "my-group", "classifications_test_enc")
    self.message_cache = []

  def set_offset(self,offset):
    self.consumer.seek(offset,0)

  def next(self):
    message = self.consumer.get_messages(count=1)
    
    print "this is the message", message

    if len(message) == 0:
      print 'returning none'
      return None
    else:
      self.current_offset = message[0].offset
      print message
      json_string = message[0].message.value
      json_string = base64.decode(json_string)
      return json.loads(json_string)

  def digest(self,classification,method=False):
      # When was this classification made?
        
        if classification is None:
          return None

        t = classification['created_at']

        # Who made the classification?
        
        # The classification will be identified by either the user_id or
        # the user_ip.  The value will be abstracted into the variable
        # Name.
        
        # Not all records have all keys.  For instance, classifications 
        # from anonymous users will not have a user_id key. We must 
        # check that the key exists, and if so, get the value.
        
        if classification.has_key('user_id'):
            Name = classification['user_id']
        else:
            # If there is no user_id, get the ip address...
            # I think we're safe with user_ip.  All records should have 
            # this field. Check the key if you're worried. 
            Name = classification['user_ip']
        
        # Pull out the subject that was classified. Note that by default
        # Zooniverse subjects are stored as lists, because they can 
        # oontain multiple images. 
        
        subjects = classification['subjects']
        
        # Ignore the empty lists (eg the first tutorial subject...)
        if len(subjects) == 0:
            return None
        
        # Get the subject ID, and also its Zooniverse ID:
        for subject in subjects:
            ID = subject['id']
            ZooID = subject['zooniverse_id']
        
        # What kind of subject was it? Training or test? A sim or a dud?
    
        if classification["training"]:
          category = 'training'
        else:
          category = "test"
        
        kind  = classification["type"]

        # What's the URL of this image?
        if classification["subjects"][0]['location']:
            location = classification['subjects'][0]['location']["standard"]
        else:
            location = None
        
        # What did the volunteer say about this subject?
        # First select the annotations:
        annotations = classification['annotations']

        # For sims, we really we want to know if the volunteer hit the 
        # arcs - but this is not yet stored in the database 
        # (issued 2013-04-23). For now, treat sims by just saying that 
        # any number of markers placed constitutes a hit.
        
        # NB: Not every annotation has an associated coordinate 
        # (e.g. x, y) - tutorials fail this criterion.

        N_markers = 0
        simFound = False
        for annotation in annotations:
            if annotation.has_key('x'): 
                N_markers += 1
        
        # Detect whether sim was found or not:
        if kind == 'sim':
            if method:
                # Use the marker positions!
                for annotation in annotations:
                    if annotation.has_key('simFound'):
                        string = annotation['simFound']
                        if string == 'true': simFound = True
            else:
                if N_markers > 0: simFound = True
        
        # Now turn indicators into results:
        if kind == 'sim':
            if simFound:
                result = 'LENS'
            else:
                result = 'NOT'
              
        elif kind == 'test' or kind == 'dud':
            if N_markers == 0:
                result = 'NOT'
            else:
                result = 'LENS'
        
        # And finally, what's the truth about this subject?
        if kind == 'sim':
            truth = 'LENS'
        elif kind == 'dud':
            truth = 'NOT'
        else:    
            truth = 'UNKNOWN'
          
        # Testing to see what people do:
        # print "In db.digest: kind,N_markers,simFound,result,truth = ",kind,N_markers,simFound,result,truth
        
        # Check we got all 9 items:            
        
        t = datetime.datetime.strptime(classification["created_at"],"%Y-%m-%d %H:%M:%S UTC")
        items = t.strftime('%Y-%m-%d_%H:%M:%S'),str(Name),str(ID),str(ZooID),category,kind,result,truth,str(location)
        if len(items) != 9: print "Kafka: digest failed: ",items[:] 
                         
        return items[:]

  def offset(self):
    return self.current_offset

  def __iter__(self):
    self.next_message()