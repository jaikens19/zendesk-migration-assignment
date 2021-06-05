import http.client
import csv
import os
import base64
import json

def set_environment_vars():
    for line in open('.env'):
        key, val = line.strip('\n').split('=')
        os.environ[key] = val

    auth = os.getenv('EMAIL_ADDRESS') + '/token:' + os.getenv('API_TOKEN')
    auth_bytes  = auth.encode('ascii')

    b64_auth_bytes = base64.b64encode(auth_bytes)
    os.environ['BASIC_TOKEN'] = b64_auth_bytes.decode('ascii')

def zendesk_fetch(endpoint, method='GET', payload=''):
    conn = http.client.HTTPSConnection(os.getenv('SUPPORT_URL'))
    headers = {
        'Authorization': 'Basic ' + os.getenv('BASIC_TOKEN'),
        'Content-Type': 'application/json'
    }
    conn.request(method, endpoint, payload, headers)
    res = conn.getresponse()
    return json.loads(res.read().decode('utf-8'))



set_environment_vars()

## print("============ Organizations: ============")

# with open('data/organizations.csv') as org_file:
#     org_reader = csv.DictReader(org_file)
#     print(org_reader)
#     for row in org_reader:
#         print(row.get('id'))



# print("============ Users: ============")

# with open('data/users.csv') as user_file:
#     user_reader = csv.reader(user_file)
#     for row in user_reader:
#         print(row[1])

# data = zendesk_fetch('/api/v2/users', 'POST', json.dumps({
#         'user': {
#            'email': 'test@test.org',
#            'name': 'Find test user' 
#         }
#     }
# ))



# print("============ Tickets: ============")

# with open('data/tickets.csv') as ticket_file:
#     ticket_reader = csv.reader(ticket_file)
#     for row in ticket_reader:
#         print(row[1])


# print("============ Ticket Comments: ============")

# with open('data/ticket_comments.csv') as ticket_comment_file:
#     ticket_comment_reader = csv.reader(ticket_comment_file)
#     for row in ticket_comment_reader:
#         print(row[1])
