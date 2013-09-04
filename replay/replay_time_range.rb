require 'rubygems'
require 'mongo'
require 'json'
require 'poseidon'
require 'Date'
require 'pry'
require 'base64'


project         = "spacewarp"
client          = Mongo::MongoClient.new 
db              = client["ouroboros"]
classifications = db["#{project}_classifications"]
subjects        = db["#{project}_subjects"]

classifications.ensure_index({:created_at=>-1})
puts "created_index "

producer = Poseidon::Producer.new(["ec2-23-22-205-190.compute-1.amazonaws.com:9092"], "project_producer")

start_date                   = Time.new(2013, 5, 7)
end_date                     = Time.new(2013, 5, 9)
speed_up                     = 1 
topic                        = "classifications_test_enc"

# classifications.find({"created_at" => {"$gt" => start_date.utc}, "created_at"=> {"$lt"=> end_date.utc}}).sort(:created_at=>-1).each do |classification|
classifications.find().sort(:created_at=>-1).each do |classification|
  subject= subjects.find({_id: classification["subject_ids"][0]}).first

  testGroup = '5154a3783ae74086ab000001'
  trainingGroup = '5154a3783ae74086ab000002'

  if subject["group_id"] == trainingGroup
    sim = true 
    type = (subject["metadata"]["training"][0]["kind"] ? 'sim' : 'dud')
  else
    sim = false
    type = 'test'
  end

  previous_classification_time ||= classification["created_at"]

  delay = classification["created_at"] - previous_classification_time 

  puts "sending #{classification.to_json}"

  classification = classification.to_hash.merge({"training" => sim, "type" => type})



  producer.send_messages [Poseidon::MessageToSend.new(topic, Base64.encode64(classification.to_json))]

  puts "sleeping for #{delay.to_f/speed_up.to_f}"

  sleep(delay.to_f/speed_up.to_f)
  previous_classification_time = classification["created_at"]

end
