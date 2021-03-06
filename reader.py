import http.client
import csv
import os
import base64
import json
import time

def none_check(value):
    return value if type(value) != type(None) and value != 'None' else ''

def ticket_status_check(ticket_status):
    if ticket_status == 'done' or ticket_status == 'retracted':
        return 'Closed'
    elif ticket_status == 'open' or ticket_status ==  'assigned':
        return 'Open'
    elif ticket_status == 'waiting':
        return'Pending'
    elif ticket_status == 'external' or ticket_status == 'engineering':
        return 'On Hold'
    elif ticket_status == 'resolved':
        return 'Solved'
    else:
        return 'New'

def convert_csv_list(lst):
    return [item.strip("'()‘’ ") for item in lst.strip('[] ').split(',')]

def zendesk_fetch(endpoint, method='GET', payload='' ):
    headers = {
        'Authorization': f'Basic {os.getenv("BASIC_TOKEN")}',
        'Content-Type': 'application/json'
    }
    api_retry_seconds = 0
    max_retries = 3
    retries = 0
    while True: 
        time.sleep(api_retry_seconds)
        conn = http.client.HTTPSConnection(os.getenv('SUPPORT_URL'))
        conn.request(method, endpoint, payload, headers)
        res = conn.getresponse()
        if res.status == 429 and retries < max_retries:
            api_retry_seconds = int(res.getheader('Retry-After'))
            retries += 1
            print(f'API Limit reached     : Retrying in {api_retry_seconds} seconds')
        else:
            break
    return json.loads(res.read().decode('utf-8'))

def zendesk_fetch_list(endpoint, method, key, lst, max_per_request=100):
    i = 0
    job_ids = []
    while i < len(lst):
        new_lst = lst[i:i+max_per_request] 
        response = zendesk_fetch(endpoint, method, json.dumps({key: new_lst}))
        ## check response status 
        ## if 429 retry after x seconds 
        job_status = response.get('job_status')
        if job_status is not None:
            job_ids.append(job_status.get('id'))
        i += max_per_request  
    ## loop through job results until all are done  
    if len(job_ids) > 0:
        while True:
            completed = True
            job_statuses = zendesk_fetch(f'/api/v2/job_statuses/show_many?ids={",".join(job_ids)}').get('job_statuses')
            for status in job_statuses:
                if status.get('status') not in ['completed', 'failed', 'killed']:
                    completed = False
                    ## wait before checking statuses again
                    time.sleep(2)
                    break
            if completed:
                break
        ## loop through job id's, make a fetch for each job, get list of results
        job_results = []
        for job in job_ids:
            job_status = zendesk_fetch(f'/api/v2/job_statuses/{job}').get('job_status')
            job_results.extend(job_status.get('results'))
        return job_results
    
def update_tag(record_type, zendesk_id, tags, overwrite=False):
    ## convert tags string to a list
    tags = convert_csv_list(tags)
    if overwrite:
        protected_tags = os.getenv('PROTECTED_TAGS').split(',')
        zendesk_tags = zendesk_fetch(f'/api/v2/{record_type}/{zendesk_id}/tags').get('tags')
        tags.extend([tag for tag in zendesk_tags if tag in protected_tags])

    ## append personal tag per instructions
    tags.append('jaikens-zendesk')
    ## add or overwrite tags
    zendesk_fetch_list(f'/api/v2/{record_type}/{zendesk_id}/tags', 'POST' if overwrite else 'PUT', 'tags', tags)

def get_dropdown_tags(field_list):
    tag_list = []
    for field in field_list:
        if field.get('type') == 'dropdown' or field.get('type') == 'tagger':
           for option in field.get('custom_field_options'):
               tag_list.append(option.get('value'))
    return tag_list

def get_protected_tags():
    tags = []
    tags_org = get_dropdown_tags(zendesk_fetch('/api/v2/organization_fields').get('organization_fields'))
    tags_user = get_dropdown_tags(zendesk_fetch('/api/v2/user_fields').get('user_fields'))
    tags_ticket = get_dropdown_tags(zendesk_fetch('/api/v2/ticket_fields').get('ticket_fields'))
    return ','.join(tags + tags_org + tags_user + tags_ticket)

def set_environment_vars():
    for line in open('.env'):
        key, val = line.strip('\n').split('=')
        os.environ[key] = val

    auth = f'{os.getenv("EMAIL_ADDRESS")}/token:{os.getenv("API_TOKEN")}'
    auth_bytes = auth.encode('ascii')

    b64_auth_bytes = base64.b64encode(auth_bytes)
    os.environ['BASIC_TOKEN'] = b64_auth_bytes.decode('ascii')

    os.environ['PROTECTED_TAGS'] = get_protected_tags()

def get_existing_orgs():
    page = 1
    while True:
        org_fetch = zendesk_fetch(f'/api/v2/organizations?page={page}')
        for org in org_fetch.get('organizations'):
            zendesk_id = org.get('id')
            org_name = org.get('name')
            domain_names = org.get('domain_names')
            if none_check(org_name) != '':
                if existing_orgs.get(org_name) is None:
                    existing_orgs[org_name] = {
                        'zendesk_id': zendesk_id, 'domain_names': domain_names}
                else:
                    existing_orgs[org_name]['zendesk_id'] = zendesk_id
        if org_fetch.get('next_page'):
            page += 1
        else:
            break

def get_existing_tickets():
    page = 1
    while True:
        ticket_fetch = zendesk_fetch(f'/api/v2/tickets?page={page}')
        for ticket in ticket_fetch.get('tickets'):
            ticket_external_id = ticket.get('external_id')
            zendesk_id = ticket.get('id')
            if ticket_external_id is not None:
                existing_tickets[ticket_external_id] = zendesk_id
        if ticket_fetch.get('next_page'):
            page += 1
        else:
            break

def zendesk_fetch_ticket_fields():
    fields = zendesk_fetch('/api/v2/ticket_fields').get('ticket_fields')
    for field in fields:
        ticket_field_dict[field.get('title')] = field.get('id')

def convert_external_to_zendesk_id(external_id):
    zendesk_id = existing_users.get(external_id)
    return zendesk_id if zendesk_id is not None else '1264164164750'

def add_membership(lst, member_type):
    endpoint = ''
    key = ''
    if member_type == 'group':
        endpoint = '/api/v2/group_memberships/create_many'
        key = 'group_memberships'
    else:
        endpoint = '/api/v2/organization_memberships/create_many'
        key = 'organization_memberships'
    zendesk_fetch_list(endpoint, 'POST', key, lst)


set_environment_vars()

start_time = time.time()

# print("============ Organizations: ============")

existing_orgs = {}
get_existing_orgs()
org_create_list = []
org_update_list = []
org_tags_list = []
new_org_tags_dict = {}


with open('data/organizations.csv') as org_file:
    zendesk_org = {}
    for csv_org in csv.DictReader(org_file):
        org_name = csv_org.get('name').strip()
        ## if name already exists update organization
        csv_org_dict = { 
                'name': none_check(org_name),
                'domain_names': convert_csv_list(none_check(csv_org.get('domain_names'))),
                'details': none_check(csv_org.get('details')),
                'notes': none_check(csv_org.get('notes')),
                'organization_fields': {
                    'region': none_check(csv_org.get('merchant_id')),
                },
        }
        if org_name in existing_orgs:
            existing_orgs[org_name]['external_id'] = none_check(csv_org.get('id')) 
            zendesk_id = existing_orgs.get(org_name).get('zendesk_id')
            if none_check(zendesk_id):
                org_tags_list.append((zendesk_id, none_check(csv_org.get('tags'))))
                csv_org_dict['id'] = zendesk_id
            for name in existing_orgs.get(org_name).get('domain_names'):
                if name not in csv_org_dict['domain_names']:
                    csv_org_dict['domain_names'].append(name)
            existing_orgs[org_name]['domain_names'] = csv_org_dict['domain_names']
            org_update_list.append(csv_org_dict)
        else:
            existing_orgs[org_name] = {'external_id': none_check(csv_org.get('id')), 'domain_names': csv_org_dict['domain_names']}
            org_create_list.append(csv_org_dict)
            ## add tags and org name to a dict
            new_org_tags_dict[org_name] = none_check(csv_org.get('tags'))
          
org_create_results = zendesk_fetch_list('/api/v2/organizations/create_many', 'POST', 'organizations', org_create_list)

get_existing_orgs()

def add_id(org):
    org['id'] = existing_orgs.get(org.get('name')).get('zendesk_id')
    return org
org_update_list = list(map(add_id, org_update_list))

zendesk_fetch_list('/api/v2/organizations/update_many', 'PUT', 'organizations', org_update_list)

for name in new_org_tags_dict:
    org_tags_list.append((existing_orgs.get(name).get('zendesk_id'), new_org_tags_dict.get(name)))

for tags in org_tags_list:
    update_tag('organizations', tags[0], tags[1])


org_time = time.time()

print('Organization Total time: ', f'{org_time - start_time}s')

# ("============ Users: ============")

existing_users = {}
## This for loop is where we populate existing user
for user in zendesk_fetch('/api/v2/users').get('users'):
    external_id = user.get('external_id')
    zendesk_id = user.get('id')
    if none_check(external_id) != '':
        ## remove from object and assign to zendesk_id
        existing_users[external_id] = zendesk_id

user_groups = {}
for group in zendesk_fetch('/api/v2/groups').get('groups'):
    group_name = group.get('name')
    zendesk_id = group.get('id')
    if none_check(zendesk_id) != '':
        user_groups[group_name] = zendesk_id

group_membership_list = []
organization_membership_list = []
user_errors_list = []
field_names = []
with open('data/users.csv') as user_file:
    for csv_user in csv.DictReader(user_file):
        zendesk_user = {}
        response = {}
        ## if external id already exitsts update user
        if csv_user.get('id') in existing_users:
            zendesk_id = existing_users.get(csv_user.get('id'))
            zendesk_user = zendesk_fetch(f'/api/v2/users/{zendesk_id}', 'PUT', json.dumps({
                'user': {
                    'external_id': none_check(csv_user.get('id')),
                    'name': none_check(csv_user.get('name')),
                    'email': none_check(csv_user.get('email')),
                    'role': none_check(csv_user.get('role')),
                    'active': none_check(csv_user.get('active')) == 'True',
                    'notes': none_check(csv_user.get('notes')),
                    'user_fields': {
                        'subscription': none_check(csv_user.get('api_subscription')),
                        'employee_id': none_check(csv_user.get('employee_id')),
                        'promotion_code': none_check(csv_user.get('promotion_code'))
                    }
                }
            }
            )).get('user')
        ## other wise we want to create a new user
        else:
            response = zendesk_fetch('/api/v2/users', 'POST', json.dumps({
                    'user': {
                       'external_id': none_check(csv_user.get('id')),
                       'name': none_check(csv_user.get('name')),
                       'email': none_check(csv_user.get('email')),
                       'role': none_check(csv_user.get('role')),
                       'active': none_check(csv_user.get('active')) == 'True',
                       'notes': none_check(csv_user.get('notes')),
                       'user_fields': {
                           'subscription': none_check(csv_user.get('api_subscription')),
                           'employee_id': none_check(csv_user.get('employee_id')),
                           'promotion_code': none_check(csv_user.get('promotion_code'))
                       }
                    }
                }
            ))
            zendesk_user = response.get('user')

        if zendesk_user is not None:
            existing_users[csv_user.get('id')] = zendesk_user.get('id')
            zendesk_id = zendesk_user.get('id')
            update_tag('users', zendesk_id, none_check(csv_user.get('tags')))
            zendesk_group_id = user_groups.get(csv_user.get('group').strip())
            group_membership_list.append({'user_id': zendesk_id, 'group_id': zendesk_group_id})
        else:
            csv_user['error'] = response.get('error')
            csv_user['details'] = response.get('details')
            csv_user['description'] = response.get('description')
            user_errors_list.append(csv_user)
            field_names = list(csv_user.keys())
        

        for org_id in convert_csv_list(csv_user.get('organization_id')):
            ## convert org_id ==> org_name ==> org zendesk_id
            for org_name in existing_orgs:
                org = existing_orgs.get(org_name)
                if org.get('external_id') == org_id:
                    organization_membership_list.append({'user_id': zendesk_id, 'organization_id': org.get('zendesk_id')})

with open('errors/user_errors.csv', 'w', newline='') as csvfile:
    
    writer = csv.DictWriter(csvfile, fieldnames=field_names)
    writer.writeheader()
    for user in user_errors_list:

        writer.writerow(user)

add_membership(group_membership_list, 'group')
add_membership(organization_membership_list, 'organization')

user_time = time.time()
print('User Total time        : ', f'{user_time - org_time}s')
# print("============ Tickets: ============")
tickets_dict = {}
ticket_field_dict = {}
tickets_tag_dict = {}
existing_tickets = {}

zendesk_fetch_ticket_fields()

with open('data/tickets.csv') as ticket_file:
    for csv_ticket in csv.DictReader(ticket_file):
        tickets_tag_dict[csv_ticket.get('id')] = {'tags': csv_ticket.get('tags')}
        tickets_dict[csv_ticket.get('id')] = {
            'external_id': csv_ticket.get('id'),
            'assignee_id': convert_external_to_zendesk_id(csv_ticket.get('assignee_id')),
            'created_at': csv_ticket.get('created_at'),
            'subject': csv_ticket.get('subject'),
            'description': csv_ticket.get('description'),
            'status': ticket_status_check(csv_ticket.get('status')),
            'submitter_id': convert_external_to_zendesk_id(csv_ticket.get('submitter_id')),
            'requester_id': convert_external_to_zendesk_id(csv_ticket.get('requester_id')),
            'updated_at': csv_ticket.get('updated_at'),
            'due_at': csv_ticket.get('due_at'),
            'custom_fields': [
                {'id': ticket_field_dict.get('About'), 'value': csv_ticket.get('about')},
                {'id': ticket_field_dict.get('Business Name'), 'value': csv_ticket.get('business name')},
                {'id': ticket_field_dict.get('Department'), 'value': csv_ticket.get('dept')},
                {'id': ticket_field_dict.get('Employee ID'), 'value': csv_ticket.get('emp id')},
                {'id': ticket_field_dict.get('Product Info'), 'value': csv_ticket.get('product information')},
                {'id': ticket_field_dict.get('Start Date'), 'value': csv_ticket.get('start date')},
                {'id': ticket_field_dict.get('Subscription'), 'value': csv_ticket.get('subscription')}
            ],
            'comments': []
        }

# print("============ Ticket Comments: ============")

with open('data/ticket_comments.csv') as ticket_comment_file:
    for csv_ticket_comment in csv.DictReader(ticket_comment_file):
        tickets_dict[csv_ticket_comment.get('parent_ticket_id')]['comments'].append({
            'author_id': convert_external_to_zendesk_id(csv_ticket_comment.get('author_id')),
            'html_body': csv_ticket_comment.get('html_body'),
            'public': csv_ticket_comment.get('public'),
            'created_at': csv_ticket_comment.get('created_at')
        })


zendesk_fetch_list('/api/v2/imports/tickets/create_many','POST', 'tickets', list(tickets_dict.values()))

get_existing_tickets()

for external_id in tickets_tag_dict:
    update_tag('tickets',  existing_tickets.get(external_id), none_check(tickets_tag_dict[external_id].get('tags')))

ticket_time = time.time()
print('Ticket Total time      : ', f'{ticket_time - user_time}s')
