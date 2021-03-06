#!/usr/bin/python
import sys, getopt
import yaml
import hashlib
import os
import jinja2
from subprocess import Popen, PIPE
import yamlordereddictloader
import jinja2schema
import validateChangeScript
from termcolor import colored

def main(argv):
  rollerScript = None
  operation = None
  try:
    opts, args = getopt.getopt(argv,"hs:o:",["rollerScript=","operation="])
  except getopt.GetoptError:
    print "Invalid Options!\nUsage: roller.py -s <rollerScript> -o <operation>"
    sys.exit(1)
  for opt, arg in opts:
    if opt == '-h':
      print 'Usage: roller.py -s <rollerScript> -o <operation>'
      sys.exit(0)
    elif opt in ("-s", "--rollerScript"):
      rollerScript = arg
    elif opt in ("-o", "--operation"):
      operation = arg
    else:
      print "Invalid Options!\nUsage: roller.py -s <rollerScript> -o <operation>"
      sys.exit(1)

  if rollerScript == None:
    print "No roller script specified!\nUsage: roller.py -s <rollerScript> -o <operation>"
    sys.exit(1)

  if operation == None:
    print "No operation specified!\nUsage: roller.py -s <rollerScript> -o <operation>"
    sys.exit(1)

  if operation not in ("deploy", "rollback"):
    print "Invalid Operation!\nUsage: roller.py -s <rollerScript> -o <operation>"
    sys.exit(1)

  validateChangeScript.run(rollerScript)

  preRequisites()

  processChangeScript(rollerScript, operation)

def preRequisites():
  if not os.path.exists("./.tmp"):
    os.makedirs("./.tmp")

def processChangeScript(rollerScript, operation, parentChange={}, parentChangeGroup={}, depth=0, data={}):
  changeScript = yaml.load(file(rollerScript,'r'), Loader=yamlordereddictloader.Loader)
  changeGroups=changeScript["changeGroups"]

  if operation == "deploy":
    for changeGroup in changeGroups:
      for change in changeGroup["changes"]:
        processChange(change, changeGroup, operation, parentChange, parentChangeGroup, depth, rollerScript, data)
  elif operation == "rollback":
    for changeGroup in reversed(changeGroups):
      for change in reversed(changeGroup["changes"]):
        processChange(change, changeGroup, operation, parentChange, parentChangeGroup, depth, rollerScript, data)

def processChange(change, changeGroup, operation, parentChange={}, parentChangeGroup={}, depth=0, rollerScript=None, data={}):
  if "name" in change:
    name=change["name"]

  if "name" in changeGroup:
    groupName=changeGroup["name"]

  if "target" in change:
    target=change["target"]
  elif "target" in changeGroup:
    target=changeGroup["target"]
  elif "target" in parentChange:
    target=parentChange["target"]
  elif "target" in parentChangeGroup:
    target=parentChangeGroup["target"]
  else:
    target=None

  if "deploy" in change:
    deploy=change["deploy"]
  elif "deploy" in changeGroup:
    deploy=changeGroup["deploy"]
  elif "deploy" in parentChange:
    deploy=parentChange["deploy"]
  elif "deploy" in parentChangeGroup:
    deploy=parentChangeGroup["deploy"]
  else:
    deploy=None

  if "rollback" in change:
    rollback=change["rollback"]
  elif "rollback" in changeGroup:
    rollback=changeGroup["rollback"]
  elif "rollback" in parentChange:
    rollback=parentChange["rollback"]
  elif "rollback" in parentChangeGroup:
    rollback=parentChangeGroup["rollback"]
  else:
    rollback=None

  if "capture" in change:
    capture=change["capture"]
  elif "capture" in changeGroup:
    capture=changeGroup["capture"]
  elif "capture" in parentChange:
    capture=parentChange["capture"]
  elif "capture" in parentChangeGroup:
    capture=parentChangeGroup["capture"]
  else:
    capture=None

  if "deploySuccessIf" in change:
    deploySuccessIf=change["deploySuccessIf"]
  elif "deploySuccessIf" in changeGroup:
    deploySuccessIf=changeGroup["deploySuccessIf"]
  elif "deploySuccessIf" in parentChange:
    deploySuccessIf=parentChange["deploySuccessIf"]
  elif "deploySuccessIf" in parentChangeGroup:
    deploySuccessIf=parentChangeGroup["deploySuccessIf"]
  else:
    deploySuccessIf=None

  if "rollbackSuccessIf" in change:
    rollbackSuccessIf=change["rollbackSuccessIf"]
  elif "rollbackSuccessIf" in changeGroup:
    rollbackSuccessIf=changeGroup["rollbackSuccessIf"]
  elif "rollbackSuccessIf" in parentChange:
    rollbackSuccessIf=parentChange["rollbackSuccessIf"]
  elif "rollbackSuccessIf" in parentChangeGroup:
    rollbackSuccessIf=parentChangeGroup["rollbackSuccessIf"]
  else:
    rollbackSuccessIf=None

  if "deploySkipIf" in change:
    deploySkipIf=change["deploySkipIf"]
  elif "deploySkipIf" in changeGroup:
    deploySkipIf=changeGroup["deploySkipIf"]
  elif "deploySkipIf" in parentChange:
    deploySkipIf=parentChange["deploySkipIf"]
  elif "deploySkipIf" in parentChangeGroup:
    deploySkipIf=parentChangeGroup["deploySkipIf"]
  else:
    deploySkipIf=None

  if "rollbackSkipIf" in change:
    rollbackSkipIf=change["rollbackSkipIf"]
  elif "rollbackSkipIf" in changeGroup:
    rollbackSkipIf=changeGroup["rollbackSkipIf"]
  elif "rollbackSkipIf" in parentChange:
    rollbackSkipIf=parentChange["rollbackSkipIf"]
  elif "rollbackSkipIf" in parentChangeGroup:
    rollbackSkipIf=parentChangeGroup["rollbackSkipIf"]
  else:
    rollbackSkipIf=None

  if "data" in parentChangeGroup:
    data.update(parentChangeGroup["data"])
  if "data" in parentChange:
    data.update(parentChange["data"])
  if "data" in changeGroup:
    data.update(changeGroup["data"])
  if "data" in change:
    data.update(change["data"])

  if "include" in change:
    includeScript=change["include"]
  elif "include" in changeGroup:
    includeScript=changeGroup["include"]
  else:
    includeScript=None

# Nested changeScripts : including changeScripts in changeScripts
# BEGIN
#      Recursive processing of nested changeScripts 
  if includeScript != None:
    processChangeScript(includeScript, operation, change, changeGroup, depth+1, data)
    return
# END

# Do nothing if a change contains no include, deploy or rollback
# BEGIN
  if deploy == None:
    if rollback == None:
      return
# END

# Execute capture before change
# BEGIN
  captureData={}
  if capture != None:
    for captureKey, captureValue in capture.iteritems():
      captureValue=jinja2.Template(captureValue).render(data)
      captureFile=open("./.tmp/"+hashlib.sha512(captureValue).hexdigest(),"w")
      captureFile.write("#!/bin/bash\n")
      captureFile.write(target + "<<" + hashlib.sha512(captureValue).hexdigest() + "\n")
      captureFile.write(captureValue + "\n")
      captureFile.write(hashlib.sha512(captureValue).hexdigest())
      captureFile.close()
      os.system("chmod a+x ./.tmp/"+hashlib.sha512(captureValue).hexdigest())
      process = Popen("./.tmp/"+hashlib.sha512(captureValue).hexdigest(), stdout=PIPE, stderr=PIPE)
      captureOutput, captureError = process.communicate()
      captureReturnCode = process.returncode
      captureData[captureKey]={ 'pre': { 'out': captureOutput, 'err':captureError, 'ret':captureReturnCode } }
      data.update(captureData)
# END
  skip=0
  result="Success"
  if operation == "rollback" and rollback != None and rollbackSkipIf != None:
    rollbackSkipIf=jinja2.Template("{{ " + rollbackSkipIf + " }}").render(data)
    if rollbackSkipIf=="True":
      result="Skipped"
      skip=1
  elif operation == "deploy" and deploy !=None and deploySkipIf != None :
    deploySkipIf=jinja2.Template("{{ " + deploySkipIf + " }}").render(data)
    if deploySkipIf=="True":
      result="Skipped"
      skip=1

# For situations where the value of a variable would contain a jinja2 reference to another variable
# BEGIN
#      Rendering jinja2 repeatedly until no change observed on further rendering
  if operation == "deploy" and deploy !=None and not skip:
    deploy=jinja2.Template(deploy).render(data)
    prev=""
    while prev!=deploy:
      prev=deploy
      deploy=jinja2.Template(deploy).render(data)
  undefinedVariables=jinja2schema.infer(deploy)
  if not undefinedVariables:
    print "Variables not defined:"
    print undefinedVariables
  if operation == "rollback" and rollback != None and not skip:
    rollback=jinja2.Template(rollback).render(data)
    prev=""
    while prev!=rollback:
      prev=rollback
      rollback=jinja2.Template(rollback).render(data)
  undefinedVariables=jinja2schema.infer(rollback)
  if not undefinedVariables:
    print "Variables not defined:"
    print undefinedVariables
# END

# For executing the change
# BEGIN
#      Generating the execution script for the change, granting execute on it and executing it
  deployData={}
  rollbackData={}
  if operation == "rollback" and rollback != None and not skip:
    changeFile=open("./.tmp/"+hashlib.sha512(rollback).hexdigest(),"w")
    changeFile.write("#!/bin/bash\n")
    changeFile.write(target + "<<" + hashlib.sha512(rollback).hexdigest() + "\n")
    changeFile.write(rollback + "\n")
    changeFile.write(hashlib.sha512(rollback).hexdigest())
    changeFile.close()
    os.system("chmod a+x ./.tmp/"+hashlib.sha512(rollback).hexdigest())
    process = Popen("./.tmp/"+hashlib.sha512(rollback).hexdigest(), stdout=PIPE, stderr=PIPE)
    rollbackOutput, rollbackError = process.communicate()
    rollbackReturnCode = process.returncode
    rollbackData['rollback']={ 'out': rollbackOutput, 'err': rollbackError, 'ret': rollbackReturnCode }
    data.update(rollbackData)
  elif operation == "deploy" and deploy !=None and not skip:
    changeFile=open("./.tmp/"+hashlib.sha512(deploy).hexdigest(),"w")
    changeFile.write("#!/bin/bash\n")
    changeFile.write(target + "<<" + hashlib.sha512(deploy).hexdigest() + "\n")
    changeFile.write(deploy + "\n")
    changeFile.write(hashlib.sha512(deploy).hexdigest())
    changeFile.close()
    os.system("chmod a+x ./.tmp/"+hashlib.sha512(deploy).hexdigest())
    process = Popen("./.tmp/"+hashlib.sha512(deploy).hexdigest(), stdout=PIPE, stderr=PIPE)
    deployOutput, deployError = process.communicate()
    deployReturnCode = process.returncode
    deployData['deploy']={ 'out': deployOutput, 'err': deployError, 'ret': deployReturnCode }
    data.update(deployData)
# END

# Execute capture after change
# BEGIN
  if capture != None:
    for captureKey, captureValue in capture.iteritems():
      captureValue=jinja2.Template(captureValue).render(data)
      captureFile=open("./.tmp/"+hashlib.sha512(captureValue).hexdigest(),"w")
      captureFile.write("#!/bin/bash\n")
      captureFile.write(target + "<<" + hashlib.sha512(captureValue).hexdigest() + "\n")
      captureFile.write(captureValue + "\n")
      captureFile.write(hashlib.sha512(captureValue).hexdigest())
      captureFile.close()
      os.system("chmod a+x ./.tmp/"+hashlib.sha512(captureValue).hexdigest())
      process = Popen("./.tmp/"+hashlib.sha512(captureValue).hexdigest(), stdout=PIPE, stderr=PIPE)
      captureOutput, captureError = process.communicate()
      captureReturnCode = process.returncode
      captureData[captureKey].update({ 'post': { 'out': captureOutput, 'err':captureError, 'ret':captureReturnCode } })
      data.update(captureData)
# END
  if operation == "rollback" and rollback != None and not skip and rollbackSuccessIf != None:
    rollbackSuccessIf=jinja2.Template("{{ " + rollbackSuccessIf + " }}").render(data)
    if rollbackSuccessIf=="True":
      result="Success"
    else:
      result="Failure"
  elif operation == "deploy" and deploy !=None and not skip and deploySuccessIf != None:
    deploySuccessIf=jinja2.Template("{{ " + deploySuccessIf + " }}").render(data) 
    if deploySuccessIf=="True":
      result="Success"
    else:
      result="Failure"


# For providing execution log
# BEGIN
#      Displaying key information about each change being executed in json format
  sys.stdout.write("{ ")
  sys.stdout.write("\"name\": \"" + name + "\", ")
  sys.stdout.write("\"group\": \"" + groupName + "\", ")
  sys.stdout.write("\"script\": \"" + rollerScript + "\", ")
  sys.stdout.write("\"depth\": " + str(depth) + ", " )
  sys.stdout.write("\"operation\": \"" + operation + "\", ")
  if result == "Success":
    sys.stdout.write("\"result\": \"" + colored(result, 'green', attrs=['bold']) + "\"")
  elif result == "Failure":
    sys.stdout.write("\"result\": \"" + colored(result, 'red', attrs=['bold']) + "\"")
  elif result == "Skipped":
    sys.stdout.write("\"result\": \"" + colored(result, 'blue', attrs=['bold']) + "\"")
  else:
    sys.stdout.write("\"result\": \"" + result + "\"")
#  sys.stdout.write("\"data\":" + str(data))
  sys.stdout.write(" }\n")
  if result == "Failure":
    sys.exit(3)

# END

if __name__ == "__main__":
  main(sys.argv[1:])
