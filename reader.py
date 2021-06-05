import csv

print("============ Organizations: ============")

with open('data/organizations.csv') as org_file:
    org_reader = csv.DictReader(org_file)
    print(org_reader)
    for key in org_reader:
        print(key)

# print("============ Users: ============")

# with open('data/users.csv') as user_file:
#     user_reader = csv.reader(user_file)
#     for row in user_reader:
#         print(row[1])


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
