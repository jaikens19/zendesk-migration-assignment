import http.client
import csv
import os
import base64
import json


def none_check(value):
    return value if type(value) != type(None) else ''


def set_environment_vars():
    for line in open('.env'):
        key, val = line.strip('\n').split('=')
        os.environ[key] = val

    auth = os.getenv('EMAIL_ADDRESS') + '/token:' + os.getenv('API_TOKEN')
    auth_bytes = auth.encode('ascii')

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


# groups = zendesk_fetch('/api/v2/groups').get('groups')
# print(groups)


external_ids = []
for user in zendesk_fetch('/api/v2/users').get('users'):
    external_id = user.get('external_id')
    if type(external_id) != type(None) and external_id != 'None':
        external_ids.append(external_id)


# user = zendesk_fetch('/api/v2/users/create_or_update', 'POST', json.dumps({
#     "user": {
#         "external_id": "1234567895",
#         "name": "TEST POST!!",
#         "email": "test@test.com",
#         "role": "end-user",
#         "active": "True",
#         "notes": "test note",
#         "user_fields": {
#             "subscription": "plan_gold",
#             "employee_id": "1991991991716161236",
#             "promotion_code": "freezendesk"
#         },
#         "tags": ["vip", "paid", "emea", "random"],
#     }
# }
# )).get('user')

# print(user.get('id'), user.get('name'))


with open('data/users.csv') as user_file:
    user_reader = csv.DictReader(user_file)
    for user in user_reader:
        # new_user
        if user.get('id') in external_ids:
            print('hereeeeeererere')
        #     new_user = zendesk_fetch('/api/v2/users/create_or_update', 'POST', json.dumps({
        #         "user": {
        #             "external_id": "1234567895",
        #             "name": "TEST POST!!",
        #             "email": "test@test.com",
        #             "role": "end-user",
        #             "active": "True",
        #             "notes": "test note",
        #             "user_fields": {
        #                 "subscription": "plan_gold",
        #                 "employee_id": "1991991991716161236",
        #                 "promotion_code": "freezendesk"
        #             },
        #             "tags": ["vip", "paid", "emea", "random"],
        #         }
        #     }
        #     )).get('user')
        else:
            external_ids.append(none_check(user.get('id')))
print(external_ids)
    #     data = zendesk_fetch('/api/v2/users', 'POST', json.dumps({
    #             'user': {
    #                'external_id': none_check(user.get('id')),
    #                'name': none_check(user.get('name')),
    #                'email': none_check(user.get('email')),
    #                'role': none_check(user.get('role')),
    #                'active': none_check(user.get('active')) == 'True',
    #                'notes': none_check(user.get('notes')),
    #                'user_fields': {
    #                    'subscription': none_check(user.get('api_subscription')),
    #                    'employee_id': none_check(user.get('employee_id')),
    #                    'promotion_code': none_check(user.get('promotion_code'))
    #                },
    #                'tags': none_check(user.get('tags')),
    #             }
    #         }
    #     ))


# print("============ Tickets: ============")

# with open('data/tickets.csv') as ticket_file:
#     ticket_reader = csv.DictReader(ticket_file)
#     for row in ticket_reader:
#         print(row[1])


# print("============ Ticket Comments: ============")

# with open('data/ticket_comments.csv') as ticket_comment_file:
#     ticket_comment_reader = csv.DictReader(ticket_comment_file)
#     for row in ticket_comment_reader:
#         print(row[1])
