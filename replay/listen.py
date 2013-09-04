from kafka.client import KafkaClient
from kafka.consumer import SimpleConsumer
import json

kafka = KafkaClient("ec2-23-22-205-190.compute-1.amazonaws.com", 9092)
consumer = SimpleConsumer(kafka, "my-group", "classifications_test3", auto_commit_every_n= 2)
# consumer.seek(30, 0)

while True :
  for message in consumer.get_messages(count=100):
    print message.message.value




