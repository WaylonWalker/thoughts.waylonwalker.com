from typing import Annotated
from fastapi.responses import RedirectResponse
from fastapi import FastAPI
from fastapi import Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from thoughts.api.post import post_router
from thoughts.api.user import user_router, User, get_current_active_user

app = FastAPI()

app.include_router(post_router)
app.include_router(user_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

login_html = '''
<!DOCTYPE html>
    <head>
        <title>thoughts login</title>
    </head>
    <body>
        <h1>login</h1>
        <form action="/login" method="POST">
            <label for="username">Username:</label>
            <input type="text" id="username" name="username">
            <label for="password">Password:</label>
            <input type="password" id="password" name="password">
            <input type="submit" value="Login">
        </form>
    </body>
</html>
'''

html = """
<html>
<!DOCTYPE html>
    <head>
        <title>thoughts</title>
    </head>
    <body>
        <h1>Thoughts</h1>
        <form id="websiteForm" action="/post/" mehod="POST" name="newPost">
            <label for="title">Title:</label>
            <input type="text" id="title" name="title" required>
            
            <label for="link">Link:</label>
            <input type="text" id="link" name="link" value="">
            
            <label for="tags">Tags:</label>
            <input type="text" id="tags" name="tags" required>
            
            <label for="message">Message:</label>
            <textarea id="message" name="message" rows="4" required></textarea>
            
            <input type="submit" value="Submit" id="submit">
        </form>
  <script>

async function postData(url = "", data = {}) {
  // Default options are marked with *
  const response = await fetch(url, {
    method: "POST", // *GET, POST, PUT, DELETE, etc.
    mode: "cors", // no-cors, *cors, same-origin
    cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
    credentials: "same-origin", // include, *same-origin, omit
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${localStorage.getItem('access_token')}`,
      // 'Content-Type': 'application/x-www-form-urlencoded',
    },
    redirect: "follow", // manual, *follow, error
    referrerPolicy: "no-referrer", // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin, same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
    body: JSON.stringify(data), // body data type must match "Content-Type" header
  });
  return response.json(); // parses JSON response into native JavaScript objects
}


    // get the form element from dom
    const formElement = document.querySelector('form#websiteForm');

    // convert the form to JSON
    const getFormJSON = (form) => {
      const data = new FormData(form);
      return Array.from(data.keys()).reduce((result, key) => {
        result[key] = data.get(key);
        return result;
      }, {});
    };

    // handle the form submission event, prevent default form behaviour, check validity, convert form to JSON
    const handler = (event) => {
      event.preventDefault();
      const valid = formElement.reportValidity();
      if (valid) {
        const result = getFormJSON(formElement);
        console.log(result)


        postData("/post/", result).then((data) => {
if (data.hasOwnProperty('detail')) {
  // Check if the value of the "detail" key is "Could not validate credentials"
  if (data.detail === 'Could not validate credentials') {
    // Redirect to the login page
    window.location.href = '/login';
  }
}
        console.log('the data', data); // JSON data parsed by `data.json()` call
        });
      }
    }


    formElement.addEventListener("submit", handler)
  </script>
    </body>
</html>
"""


@app.get("/")
async def get():
    return HTMLResponse(html)
