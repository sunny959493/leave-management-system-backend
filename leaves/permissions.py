from graphql import GraphQLError

class IsAdmin:
    message = "only admins can access"

    @staticmethod
    def has_permission(user):
        return user.is_authenticated and user.is_staff
    
class IsAuthenticated:
    message = "only authenticated users can access"

    @staticmethod
    def has_permission(user):
        return user.is_authenticated



def permission_required(permission_class):
    def decorator(func):
        def wrapper(self, info, *args, **kwargs):
            user = info.context.user
            if not permission_class.has_permission(user):
                raise GraphQLError(permission_class.message)
            return func(self, info, *args, **kwargs)
        return wrapper
    return decorator