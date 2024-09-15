import os
def getUserIdEmail(request):
    if (os.environ.get("DEBUG") == "True" ):
        print("Deployment Server Running")
        cookies_header = request.headers.get('Cookies')
    else:
        print("Local Server Running")
        email = request.COOKIES.get('email')
        user_id = request.COOKIES.get('userId')
        return user_id, email
    if cookies_header:
        # Initialize a dictionary to store parsed cookies
        cookies = {}

        # Split the cookie string on ';' to separate individual cookies
        for cookie in cookies_header.split(';'):
            # Strip whitespace and split each cookie into key-value pairs
            name, value = cookie.strip().split('=', 1)
            cookies[name] = value

        # Now you can access the individual cookies:
        email = cookies.get('email')
        user_id = cookies.get('userId')
        if user_id and email:
            return user_id, email
        return None, None
    return None, None