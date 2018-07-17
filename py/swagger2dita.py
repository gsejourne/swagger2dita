#!/usr/bin/env python

import os, sys, getopt, pprint
import mimetypes, yaml, json
mime = mimetypes.MimeTypes()

# Configure Output dir and files
if not os.path.exists('./dist/refs'):
  os.makedirs('./dist/refs')

mapList = open('./dist/maps.list','a')

def parseInput(file):
  mimeType = mime.guess_type(file)[0]
  with open(file, 'r') as stream:
    if mimeType == 'application/json':
      data = json.load(stream)
    else: # assume it's a Yaml file
      try:
        data = yaml.load(stream)
      except yaml.YAMLError as exc:
        print(exc)
    writeStruct(data)
    writeDefs(data)
    writeParams(data)


def writeStruct(data):
  info = data['info']
  if 'tags' in data:
    tags = data['tags']
  else:
    tags = None
  schemes = data['schemes']
  if 'paths' in data:
    paths = data['paths']
  else:
    print("! Not generating " + data['info']['title'] +': No paths declared!')
    exit(0)

  writeMap(data)

def writeMap(data):
  cleanTitle = data['info']['title'].replace(' ','_').replace('/','_')
  mapFile = cleanTitle + '.ditamap'
  distMap = open('./dist/' + mapFile, 'w')
  mapList.write('<chapter navtitle="'+ data['info']['title'] +'" format="ditamap" href="'+ mapFile +'"/>\n')
  print('* Generating Map file: ' + './dist/'+ mapFile)
  distMap.write('<?xml version="1.0" encoding="UTF-8"?>\n\
<!DOCTYPE map PUBLIC "-//OASIS//DTD DITA Map//EN" "map.dtd">\n\
<map>\n\
  <title>'+ data['info']['description'] +'</title>\n\
  <topicref processing-role="resource-only" keys="params" href="refs/PARAMS_' + cleanTitle + '.dita"/>\n\
  <topicref processing-role="resource-only" keys="refs" href="refs/REFS_' + cleanTitle + '.dita"/>\n\
  <topichead navtitle="'+ data['info']['title'] +'">\n')
  # Chapters
  topics = writePaths(data['paths'])
  distMap.write(topics)
  distMap.write('\t</topichead>\n</map>\n')
  distMap.close()

def writePaths(data):
  topics = ''
  for p in data:
    path = (p.replace('{','').replace('}','')).rsplit('/',1)
    print('* Writing file ' + './dist' + path[0] + '/' + path[1] + '.dita')
    # Create subdirs:
    if not os.path.exists('./dist' + path[0]):
      os.makedirs('./dist' + path[0])
    # Create file:
    pFile = open('./dist' + path[0] + '/' + path[1] + '.dita', 'w')
    # Append file to map:
    topics = topics + '\t<topicref href="'+ path[0][1:] + '/' + path[1] + '.dita"/>\n'
    # Create topic file for endpoint:
    topic = getTopic(p,data[p])
    pFile.write(topic)
    pFile.close()
  return topics

def getTopic(p,d):
  # pprint.pprint(d)
  for verb in d:
    out = '<?xml version="1.0" encoding="UTF-8"?>\n\
<!DOCTYPE topic PUBLIC "-//OASIS//DTD DITA Topic//EN" "topic.dtd">\n\
<topic id="' + p.rsplit('/',1)[1].replace('{','').replace('}','').replace('.','') + '">\n\
  <title>' + verb.upper() + ' ' + p + '</title>\n'
    if 'summary' in d[verb]:
      out = out + '\t<shortdesc>' + d[verb]['summary'] + '</shortdesc>\n'
    elif 'description' in d[verb]:
      out = out + '\t<shortdesc>' + d[verb]['description'] + '</shortdesc>\n'
    out = out + '\t<prolog>\n\
    <metadata>\n\
      <keywords>\n\
        <indexterm>'+ p.rsplit('/',1)[1] +'</indexterm>\n\
      </keywords>\n\
      <data name="verb">' + verb.upper() + '</data>\n\
      <data name="resource">' + p + '</data>\n\
    </metadata>\n\
  </prolog>\n\
  <body>\n\
    <section class="+ vs/parameters ">\n\
      <div class="+ vs/api http/headers ">\n'
    if 'consumes' in d[verb]:
      out = out + writeHeaders(d[verb]['consumes'],d[verb]['parameters'],d[verb]['produces'])
    elif 'parameters' in d[verb]:
      out = out + writeHeaders(None,d[verb]['parameters'],d[verb]['produces'])
    elif 'produces' in d[verb]:
      out = out + writeHeaders(None,None,d[verb]['produces'])
    out = out + '</div>\n'
    if len(d[verb]['parameters']) > 0:
      out = out + '<div class="+ vs/api http/fields ">\n\
      ' + writeFields(d[verb]['parameters']) + '\
      </div>\n'
    out = out + '</section>\n\
    <section class="+ vs/return ">\n\
      <div class="+ vs/api http/codes ">\n'
    if 'responses' in d[verb]:
      out = out + writeCodes(d[verb]['responses'],d[verb]['produces'])
    out = out + '</div>\n\
    </section>\n\
  </body>\n\
</topic>\n'
    return out

def writeCodes(codes,produce):
  # pprint.pprint(codes)
  out = '<parml>\n'
  for c in codes:
    out = out + '<plentry>\n\
      <pt class="+ vs/api http/code ">'+ str(c) +'</pt>\n'
    if len(produce) > 0:
      out = out + '<pd class="+ vs/api http/type ">'+ produce[0] +'</pd>\n'
    if 'description' in codes[c]:
      out = out + '<pd class="+ vs/api http/msg ">OK</pd>'
    if 'schema' in codes[c]:
      out = out + '<pd><parml>\n\
        <plentry conkeyref="refs/' + (codes[c]['schema']['$ref'].rsplit('/',1)[1]).replace('.','').replace(' ','_').replace('/','_') + '"><pt/><pd/></plentry>\n\
        </parml></pd>\n'
    out = out + '</plentry>'
  out = out + '</parml>\n'
  return out

def writeHeaders(consume, params, produce):
  out = '<parml>\n'
  if consume:
    out = out + '<plentry>\n\
      <pt>Content-Type</pt>\n\
      <pd><codeph>'+ consume[0] +'</codeph></pd>\n\
      <pd>This header is optional as the API expects a JSON blob by default.</pd>\n\
    </plentry>'
  if produce:
    out = out + '<plentry>\n\
      <pt>Accept</pt>\n\
      <pd><codeph>'+ produce[0] +'</codeph></pd>\n\
      <pd>This header is optional as the API returns a JSON blob by default.</pd>\n\
    </plentry>'
  for h in params:
    if h['in'] == 'header':
      out = out + '<plentry'
      if 'required' in h:
        out = out + ' importance="required"'
      out = out + '>\n\
        <pt>'+ h['name'] +'</pt>\n\
        <pd><codeph>'+ h['type'] +'</codeph></pd>\n'
      if 'description' in h:
        out = out + '<pd>'+ h['description'] +'</pd>\n'
      out = out + '</plentry>\n'
  out = out + '</parml>\n'
  return out

def writeFields(params):
  out = '<parml>\n'
  for h in params:
    if h['in'] != 'header':
      out = out + '<plentry'
      if 'required' in h:
        out = out + ' importance="required"'
      out = out + '>\n\
        <pt>'+ h['name'] +'</pt>\n'
      if 'type' in h:
        out = out + '<pd><codeph>'+ h['type'] +'</codeph></pd>\n'
      elif 'schema' in h:
        out = out + '<pd><parml>\n\
          <plentry conkeyref="refs/'+ (h['schema']['$ref'].rsplit('/',1)[1]).replace('.','').replace(' ','_') +'"><pt/><pd/></plentry>\n\
        </parml></pd>\n'
      if 'description' in h:
        out = out + '<pd>'+ h['description'] +'</pd>\n'
      out = out + '</plentry>\n'
  out = out + '</parml>\n'
  return out

def writeDefs(data):
  refFile = 'REFS_' + data['info']['title'].replace(' ','_').replace('/','_') + '.dita'
  distDefs = open('./dist/refs/' + refFile,'w')
  print('* Generating Definitions file: ' + './dist/refs/' + refFile)
  distDefs.write('<?xml version="1.0" encoding="UTF-8"?>\n\
    <!DOCTYPE topic PUBLIC "-//OASIS//DTD DITA Topic//EN" "topic.dtd">\n\
    <topic id="apiref_ref_params">\n')
  distDefs.write('\t<title>Reusable referenced fields</title>\n')
  distDefs.write('\t<body>\n')
  
  # pprint.pprint(data['parameters'],)
  if 'definitions' in data:
    distDefs.write('\t\t<div class="+ vs/api http/fields ">\n')
    distDefs.write('\t\t\t<parml>\n')
    for k in data['definitions']:
      reqs = []
      if 'required' in data['definitions'][k]:
        reqs = data['definitions'][k]['required']
      out = getField(k,data['definitions'][k],reqs)
      
      distDefs.write(out)
    distDefs.write('\t\t\t</parml>\n')
    distDefs.write('\t\t</div>\n')

  distDefs.write('\t</body>\n')
  distDefs.write('</topic>\n')
  distDefs.close()

def writeParams(data):
  refFile = 'PARAMS_' + data['info']['title'].replace(' ','_').replace('/','_') + '.dita'
  distParams = open('./dist/refs/' + refFile,'w')
  print('* Generating Global parameters file: ' + './dist/refs/' + refFile)
  distParams.write('<?xml version="1.0" encoding="UTF-8"?>\n\
    <!DOCTYPE topic PUBLIC "-//OASIS//DTD DITA Topic//EN" "topic.dtd">\n\
    <topic id="apiref_ref_params">\n')
  distParams.write('\t<title>Reusable referenced parameters</title>\n')
  distParams.write('\t<body>\n')
  if 'parameters' in data:
    distParams.write('\t\t<div class="+ vs/api http/fields ">\n')
    distParams.write('\t\t\t<parml>\n')
    # pprint.pprint(data['parameters'],)
    for k in data['parameters']:
      ko = data['parameters'][k]
      out = '\t\t\t\t<plentry id="' + str(k).replace('.','').replace('/','_') + '"'
      if 'required' in ko:
        out = out + ' importance="required"'
      
      out = out + '>\n\
            <pt><varname>' + ko['name'] + '</varname></pt>\n\
            <pd class="+ vs/api http/type ">' + ko['type'] + '</pd>\n'
    
      out = out + '\t\t\t\t\t<pd>' + ko['description']
      
      if 'enum' in ko:
        out = out + '. Allowed values are <ul>'
        for v in ko['enum']:
          out = out + '<li><userinput>' + str(v) + '</li></userinput>'
        out = out + '</ul>'
      out = out + '</pd>\n'
      if 'default' in ko:
        out = out + '\t\t\t\t\t<pd>Default value is <systemoutput>' + str(ko['default']) + '</systemoutput></pd>\n'
      
      out = out + '\t\t\t\t</plentry>\n'
      distParams.write(out)

    distParams.write('\t\t\t</parml>\n')
    distParams.write('\t\t</div>\n')
  distParams.write('\t</body>\n')
  distParams.write('</topic>\n')
  distParams.close()

def getField(k,d,req):
  out = '\t\t\t\t<plentry id="' + str(k).replace(' ','_').replace('.','').replace('/','_') + '">\n\
        <pt><varname>' + k + '</varname></pt>\n\
        <pd class="+ vs/api http/type ">' + d['type'] + '</pd>\n'
  
  out = out + '\t\t\t\t\t<pd>'
  
  if 'description' in d:
    out = out + d['description']

  if 'properties' in d:
    out = out + '<parml>\n'
    for p in d['properties']:
      out = out + getProp(p,d['properties'][p],req)
    out = out + '</parml>'
  
  out = out + '</pd>\n'
  
  out = out + '\t\t\t\t</plentry>\n'

  return out

def getProp(p,d,req):
  prop = '\t\t\t\t\t<plentry'
  if len(req) > 0:
    if p in req:
      prop = prop + ' importance="required"'

  prop = prop + '>\n\t\t\t\t\t\t<pt><varname>' + p + '</varname></pt>\n'

  if 'type' in d:
    prop = prop + '<pd class="+ vs/api http/type ">' + d['type'] + '</pd>\n<pd>'
  else:
    prop = prop + '<pd>'

  if 'description' in d:
    prop = prop + d['description']

  if 'enum' in d:
    prop = prop + '. Possible values are <ul>'
    for v in d['enum']:
      prop = prop + '<li><userinput>' + str(v) + '</userinput></li>'
    prop = prop + '</ul>'

  if '$ref' in d:
    ref = d['$ref'].rsplit('/',1)[1].replace('.','').replace(' ','_')
    prop = prop + '<parml>\
      <plentry conref="#apiref_ref_params/' + ref + '"><pt/><pd/></plentry></parml>\n'
  
  prop = prop + '</pd>\n'
  if 'default' in d:
    prop = prop + '\t\t\t\t\t<pd>Default value is <systemoutput>' + str(ko['default']) + '</systemoutput></pd>\n'
  
  prop = prop + '\t\t\t\t\t</plentry>\n'
  return prop

def main(argv):
  inputfile = ''
  try:
    opts, args = getopt.getopt(argv,"hi:",["ifile="])
  except getopt.GetoptError:
    print ('swagger2dita.py -i <inputfile>')
    sys.exit(2)
  for opt, arg in opts:
    if opt == '-h':
      print ('Usage: test.py -i <inputfile>')
      sys.exit()
    elif opt in ("-i", "--ifile"):
      inputfile = arg
  if len(opts) > 0:
    # print ('Input file is "', inputfile, '"')
    parseInput(inputfile)
  else:
    print ('Usage: test.py -i <inputfile>')
    sys.exit()

if __name__ == "__main__":
  main(sys.argv[1:])