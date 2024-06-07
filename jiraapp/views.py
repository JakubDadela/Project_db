from django.shortcuts import render, redirect
from bson import ObjectId
from datetime import datetime

def home(request):
    db_client = request.db_client  # Pobranie klienta bazy danych z obiektu żądania

    # Uzyskanie dostępu do bazy danych MongoDB
    db = db_client['JiraDb']

    # Wykonaj zapytanie do kolekcji MongoDB
    collection = db['projects']
    data = list(collection.find())  # Zamień wynik zapytania na listę
    projects_list=list()
    for project in data:
        project['id'] = project['_id']
        projects_list.append(project)

    return render(request, 'home.html', {'projects': projects_list})

def add_project_view(request):
    db_client = request.db_client  # Pobranie klienta bazy danych z obiektu żądania
    db = db_client['JiraDb']

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        status = request.POST.get('status')
        assigned_to = list(map(ObjectId, request.POST.getlist('users')))
        project_dict = {
            'name': name,
            'description': description,
            'start_date': start_date,
            'end_date': end_date,
            'status': status,
            'assigned_users': assigned_to,
            'tasks': []
        }
        project_id = db['projects'].insert_one(project_dict).inserted_id

        # Przypisz użytkowników do projektu
        for user_id in assigned_to:
            db['users'].update_one(
                {'_id': user_id},
                {'$push': {'assigned_projects': project_id}}
            )

        return redirect('/')
    
    statuses_set = set(('to do', 'in progress', 'finished'))
    users = db['users'].find()
    users_list = list()
    for user in users:
        if user['_id'] != ObjectId('66632a552c023333dbdc74a0'):
            user['id'] = user['_id']
            users_list.append(user)
    return render(request, 'add_project_view.html', context={'statuses': statuses_set, 'users': users_list})


def project_view(request, project_id=None):
    db_client = request.db_client
    db = db_client['JiraDb']
    project = db['projects'].find_one({'_id': ObjectId(project_id)})
    tasks = project['tasks']

    tasks_list = []
    for task in tasks:
        task['id'] = task['_id']
        assignee = db['users'].find_one({'_id': ObjectId(task['assigned_to'])})
        if assignee is None:
            filter = {"_id": ObjectId(project_id)}
            project = db['projects'].find_one({'_id': ObjectId(project_id)})
            index = [row['_id'] for row in project['tasks']].index(ObjectId(task['id']))
            update = {"$set": {f"tasks.{index}.assigned_to": ObjectId('66632a552c023333dbdc74a0')}}
            db['projects'].update_one(filter, update)
            assignee = db['users'].find_one({'_id': ObjectId('66632a552c023333dbdc74a0')})
        elif ObjectId(project_id) not in assignee['assigned_projects']:
            project = db['projects'].find_one({'_id': ObjectId(project_id)})
            filter = {"_id": ObjectId(project_id)}
            index = [row['_id'] for row in project['tasks']].index(ObjectId(task['id']))
            old_user = project['tasks'][index]['assigned_to']
            update = {"$set": {f"tasks.{index}.assigned_to": ObjectId('66632a552c023333dbdc74a0')}}
            db['projects'].update_one(filter, update)
            assignee = db['users'].find_one({'_id': ObjectId('66632a552c023333dbdc74a0')})

            old_user_query = {'_id': ObjectId(old_user)}
            update_query = {
                '_id': ObjectId('66632a552c023333dbdc74a0')
            }

            pop_query = {
                '$pull': {
                    'assigned_task': ObjectId(task['id'])
                }
            }
            
            push_query = {
                '$push': {
                    'assigned_task': ObjectId(task['id'])
                }
            }
            db['users'].update_one(old_user_query, pop_query)
            db['users'].update_one(update_query, push_query)

        task['assignee_name'] = assignee['name']
        tasks_list.append(task)

    task_counts = get_task_counts_by_status(db, project_id)
    
    return render(request, 'project.html', context={
        'project_name': project['name'],
        'project_id': project_id,
        'tasks': tasks_list,
        'task_counts': task_counts
    })
    
def addTaskView(request, project_id=None):
    db_client = request.db_client
    db = db_client['JiraDb']

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        due_date = request.POST.get('due_date')
        status = request.POST.get('status')
        assigned_to = request.POST.get('assigned_to')
        labels = request.POST.getlist('labels')
        
        if labels is None:
            labels = []
        while '' in labels:
            labels.remove('')
        if len(labels) != 0:
            labels = list(map(ObjectId, labels))

        add_new_task(db, name, description, due_date, status, ObjectId(assigned_to), ObjectId(project_id), labels)
        
        project = db['projects'].find_one({'_id': ObjectId(project_id)})
        filter = {'_id': ObjectId(assigned_to)}
        push = {'assigned_task': project['tasks'][-1]['_id']}
        db['users'].update_one(filter, {"$push": push})
        
        return redirect(f'/project/{project_id}')
    
    project = db['projects'].find_one({'_id': ObjectId(project_id)})
    users = db['users'].find()
    users_list = []
    statuses_set = set(('to do', 'in backlog', 'analyze', 'development', 'completed'))

    for user in users:
        user['id'] = user['_id']
        if ObjectId(project_id) in user.get('assigned_projects', []):
            users_list.append(user)
    
    labels = db['labels'].find()
    labels_list = []
    for label in labels:
        label['id'] = label['_id']
        labels_list.append(label)

    return render(request, 'add_task.html', context={
        'project_name': project['name'], 'users': users_list, 'statuses': statuses_set, 'project_id': project_id,
        'labels': labels_list
    })

    
def addLabelView(request):
    db_client = request.db_client
    db = db_client['JiraDb']
    if request.method == 'POST':
        name = request.POST.get('labelName')
        color = request.POST.get('labelColor')
        db['labels'].insert_one({'name': name, 'color': color})
        return redirect('/')
    return render(request, 'add_labels.html')

def usersView(request):
    db_client = request.db_client
    db = db_client['JiraDb']
    
    # Agregacja po stronie MongoDB
    pipeline = [
        {
            '$match': {
                '_id': {'$ne': ObjectId('66632a552c023333dbdc74a0')}
            }
        },
        {
            '$lookup': {
                'from': 'projects',
                'localField': 'assigned_projects',
                'foreignField': '_id',
                'as': 'projects'
            }
        },
        {
            '$addFields': {
                'project_count': {'$size': '$projects'}
            }
        },
        {
            '$project': {
                'name': 1,
                'email': 1,
                'role': 1,
                'project_count': 1
            }
        }
    ]
    
    users = list(db['users'].aggregate(pipeline))
    users_list = list()
    for user in users:
        user['id'] = user['_id']
        users_list.append(user)
    
    return render(request, 'users.html', {'users': users_list})

def createUserView(request):
    db_client = request.db_client
    db = db_client['JiraDb']
    if request.method == 'POST':
        name = request.POST['name']
        email = request.POST['email']
        password = request.POST['password']
        role = request.POST['role']
        projects = request.POST.getlist('assigned_projects')
        user = {'name': name, 'email': email, 'password': password, 'role': role, 'assigned_task': [], 'assigned_projects': list(map(ObjectId, projects))}
        data = db['users'].insert_one(user)
        for project_id in projects:
            project = db['projects'].find_one({"_id": ObjectId(project_id)})
            project['assigned_users'].append(ObjectId(data.inserted_id))
            db['projects'].update_one({"_id": ObjectId(project_id)}, {"$set": project})
        return redirect('users')
    project_list=[]
    for project in db['projects'].find():
        project['id'] = project['_id']
        project_list.append(project)
    return render(request, 'user_create.html', context={'projects': project_list})
        
def deleteUser(request, user_id=None):
    db_client = request.db_client
    db = db_client['JiraDb']
    
    user = db['users'].find_one({'_id': ObjectId(user_id)})

    assigned_projects = user.get('assigned_projects', [])
    for project_id in assigned_projects:
        projects_collection = db['projects']
        project = projects_collection.find_one({"_id": ObjectId(project_id)})
        if project:
            project['assigned_users'].remove(ObjectId(user_id))
            projects_collection.update_one({"_id": ObjectId(project_id)}, {"$set": project})

    db['users'].delete_one({'_id': ObjectId(user_id)})
    return redirect('users')

def editUser(request, user_id=None):
    db_client = request.db_client
    db = db_client['JiraDb']
    
    user = db['users'].find_one({'_id': ObjectId(user_id)})

    if request.method == 'POST':
        name = request.POST['name']
        email = request.POST['email']
        password = request.POST['password']
        role = request.POST['role']
        projects = request.POST.getlist('assigned_projects')

        current_projects = user.get('assigned_projects', [])
        current_tasks = user.get('assigned_task', [])

        # Remove old projects
        for project_id in current_projects:
            projects_collection = db['projects']
            project = projects_collection.find_one({"_id": ObjectId(project_id)})
            if project:
                project['assigned_users'].remove(ObjectId(user_id))
                projects_collection.update_one({"_id": ObjectId(project_id)}, {"$set": project})

        updated_user = {
            'name': name,
            'email': email,
            'password': password,
            'role': role,
            'assigned_task': current_tasks,
            'assigned_projects': list(map(ObjectId, projects))
        }
        db['users'].update_one({'_id': ObjectId(user_id)}, {'$set': updated_user})

        # Add new projects
        assigned_projects = db['users'].find_one({'_id': ObjectId(user_id)}).get('assigned_projects', [])
        for project_id in assigned_projects:
            projects_collection = db['projects']
            project = projects_collection.find_one({"_id": ObjectId(project_id)})
            if project:
                project['assigned_users'].append(ObjectId(user_id))
                projects_collection.update_one({"_id": ObjectId(project_id)}, {"$set": project})

        return redirect('users')

    project_list = list(db['projects'].find())
    for project in project_list:
        project['id'] = project['_id']

    return render(request, 'edit_user.html', {'user': user, 'projects': project_list})

def taskView(request, project_id=None, task_id=None):
    db_client = request.db_client
    db = db_client['JiraDb']
    if request.method == 'POST':     
        if request.POST.get('new_user'):
            new_assignee = request.POST.get('new_user')
            project = db['projects'].find_one({'_id': ObjectId(project_id)})
            filter = {"_id": ObjectId(project_id)}
            index = [row['_id'] for row in project['tasks']].index(ObjectId(task_id))
            old_user = project['tasks'][index]['assigned_to']
            update = {"$set": {f"tasks.{index}.assigned_to": ObjectId(new_assignee)}}
            db['projects'].update_one(filter, update)

            old_user_query = {'_id': ObjectId(old_user)}
            update_query = {'_id': ObjectId(new_assignee)}

            pop_query = {'$pull': {'assigned_task': ObjectId(task_id)}}
            push_query = {'$push': {'assigned_task': ObjectId(task_id)}}
            
            db['users'].update_one(old_user_query, pop_query)
            db['users'].update_one(update_query, push_query)

        elif request.POST.get('new_status'):
            new_status = request.POST.get('new_status')
            project = db['projects'].find_one({'_id': ObjectId(project_id)})
            filter = {"_id": ObjectId(project_id)}
            index = [row['_id'] for row in project['tasks']].index(ObjectId(task_id))
            update = {"$set": {f"tasks.{index}.status": new_status}}
            db['projects'].update_one(filter, update)

        elif request.POST.get('new_comment'):
            new_comment = request.POST.get('new_comment')
            commentator = ObjectId('66632a552c023333dbdc74a0')
            add_new_comment(request, new_comment, datetime.now(), commentator, ObjectId(project_id), ObjectId(task_id))
        
        elif request.POST.get('comment_id'):
            project = db['projects'].find_one({'_id': ObjectId(project_id)})
            comment_id = request.POST.get('comment_id')
            index = [row['_id'] for row in project['tasks']].index(ObjectId(task_id))
            db['projects'].update_one(
                {"_id": ObjectId(project_id)},
                {"$pull": {f"tasks.{index}.comments": {"_id": ObjectId(comment_id)}}}
            )
        else:
            return redirect(f'/project/{project_id}/')

    project = db['projects'].find_one({'_id': ObjectId(project_id)})
    users = project['assigned_users']
    users_list = []
    task = next((row for row in project.get('tasks', []) if row.get('_id') == ObjectId(task_id)), None)
    if task:
        assignee = db['users'].find_one({'_id': ObjectId(task.get('assigned_to', ''))})
        if assignee:
            assignee_name = assignee.get('name', '')
            for user in users:
                user_name = db['users'].find_one({'_id': user})
                if user_name and str(task.get('assigned_to')) != str(user):
                    users_list.append({'user_name': user_name.get('name', ''), 'user_id': user})
    comments_list = []
    if task and 'comments' in task:
        comments = task['comments']
        for comment in comments:
            user_name = db['users'].find_one({'_id': ObjectId(comment.get('user_id', ''))})
            if user_name:
                comment['user'] = user_name.get('name', '')
                comment['id'] = comment.get('_id', '')
                comments_list.append(comment)

    label_selected = []
    label_existing = [] 
    for label in task['assigned_labels']:
        row = db['labels'].find_one({'_id': ObjectId(label)})
        row['id'] = row['_id']
        label_selected.append(row)

    for label in db['labels'].find():
        label['id'] = label['_id']
        if label not in label_selected:
            label_existing.append(label)

    task['id'] = task['_id']
    statuses = ["analyze", "completed", "development", "to do", "in backlog"]

    return render(request, 'task.html', context={
        'task': task, 'users': users_list, 'assignee': assignee, 'comments': comments_list, 
        'labels': label_selected, 'project_id': project_id, 'existing_labels': label_existing, 'statuses': statuses
    })


def add_new_comment(request, text, date, user_id, project_id, task_id):
    db_client = request.db_client
    db = db_client['JiraDb']
    project = db['projects'].find_one({'_id': ObjectId(project_id)})
    index = [row['_id'] for row in project['tasks']].index(ObjectId(task_id))
    comment_dict = {
        '_id': ObjectId(), 'text': text, 'date': date, 'user_id': user_id}
    return db['projects'].update_one(
    {"_id": project_id},
    {"$push": {f"tasks.{index}.comments": comment_dict}}
    )
    
def add_new_task(db, name, description, due_date, status, assigned_to, project_id, assigned_labels=[], comments=[]):
    task_dict = {
        '_id': ObjectId(), 'name': name, 'description': description, 'due_date': due_date, 'status': status,
        'assigned_to': assigned_to, 'project_id': project_id, 'assigned_labels': assigned_labels, 'comments': comments}
    return db['projects'].update_one(
    {"_id": project_id},
    {"$push": {f"tasks": task_dict}}
    )
    
def add_user_to_project_view(request, project_id=None):
    db_client = request.db_client
    db = db_client['JiraDb']

    exclude_user_id = ObjectId('66632a552c023333dbdc74a0')

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        if ObjectId(user_id) != exclude_user_id:
            db['projects'].update_one(
                {'_id': ObjectId(project_id)},
                {'$push': {'assigned_users': ObjectId(user_id)}}
            )
            db['users'].update_one(
                {'_id': ObjectId(user_id)},
                {'$push': {'assigned_projects': ObjectId(project_id)}}
            )
        return redirect(f'/project/{project_id}')

    project = db['projects'].find_one({'_id': ObjectId(project_id)})
    assigned_users_ids = project.get('assigned_users', [])

    # Pobierz wszystkich użytkowników, którzy nie są przypisani do projektu i nie mają wykluczonego ID
    users = db['users'].find({
        '_id': {'$nin': assigned_users_ids + [exclude_user_id]}
    })
    user_list = [{'id': user['_id'], 'name': user['name']} for user in users]

    return render(request, 'add_user_to_project.html', {'users': user_list, 'project_id': project_id})
    
def get_task_counts_by_status(db, project_id):
    pipeline = [
        {'$match': {'_id': ObjectId(project_id)}},  # Dopasowanie projektu po ID
        {'$unwind': '$tasks'},  # Rozwija listę zadań
        {'$group': {'_id': '$tasks.status', 'count': {'$sum': 1}}}  # Grupowanie po statusie zadań i liczenie ich
    ]
    result = db['projects'].aggregate(pipeline)
    task_counts = [{'status': item['_id'], 'count': item['count']} for item in result]
    
    return task_counts

def addNewLabelView(request, task_id=None):
    db_client = request.db_client
    db = db_client['JiraDb']
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        label_id = request.POST.get('label_id')
        project =db['projects'].find_one({'_id': ObjectId(project_id)})
        index = [row['_id'] for row in project['tasks']].index(ObjectId(task_id))
        db['projects'].update_one(
            {"_id": ObjectId(project_id)},
            {"$push": {f"tasks.{index}.assigned_labels": ObjectId(label_id)}})
    return redirect(f'/project/{project_id}/task/{task_id}')

def deleteLabelView(request, task_id=None):
    db_client = request.db_client
    db = db_client['JiraDb']
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        label_id = request.POST.get('label_id')
        project = db['projects'].find_one({'_id': ObjectId(project_id)})
        index = [row['_id'] for row in project['tasks']].index(ObjectId(task_id))
        db['projects'].update_one(
            {"_id": ObjectId(project_id)},
            {"$pull": {f"tasks.{index}.assigned_labels": ObjectId(label_id)}})
    return redirect(f'/project/{project_id}/task/{task_id}')

def remove_user_from_project_view(request, project_id=None):
    db_client = request.db_client
    db = db_client['JiraDb']
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        db['projects'].update_one(
            {'_id': ObjectId(project_id)},
            {'$pull': {'assigned_users': ObjectId(user_id)}}
        )
        db['users'].update_one(
            {'_id': ObjectId(user_id)},
            {'$pull': {'assigned_projects': ObjectId(project_id)}}
        )
        return redirect(f'/project/{project_id}')
    
    project = db['projects'].find_one({'_id': ObjectId(project_id)})
    users = project.get('assigned_users', [])
    user_list = [{'id': user, 'name': db['users'].find_one({'_id': user})['name']} for user in users]
    
    return render(request, 'remove_user_from_project.html', {'users': user_list, 'project_id': project_id})
