groups = [group.name for group in user.ak_groups.all()]
user_attributes = user.group_attributes()

if 'App Admins' in groups:
  groups.append('admin')

return {
  **user_attributes.get('profile', {}), 
  "name": request.user.name,
  'groups': groups,
}