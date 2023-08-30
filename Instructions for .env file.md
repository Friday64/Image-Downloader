# Setting up the .env File

The .env file is a simple and effective way to manage and secure environment variables in your application. It helps to protect sensitive information like API keys, database passwords, and other credentials.
In this application, you are using the Flickr API. Therefore, we need to store the API Key and Secret Key in a safe place. Storing it directly in the code is not a safe practice. Instead, we use a .env file to keep these keys and load them when we run the application.

## Setup

To setup your .env file, follow these steps:
- Step 1: Create the .env File
In the same directory as your Python script, create a new file named .env.
- Step 2: Add Your API Keys to the .env File
Open the .env file in a text editor and add your Flickr API Key and Secret Key in the following format:

```makefileCopy code
FLICKR_API_KEY=your_api_key_here
FLICKR_API_SECRET=your_api_secret_here
```

Replace `your_api_key_here` and `your_api_secret_here` with your actual Flickr API Key and Secret Key. Be sure not to include any extra spaces or quotation marks.

- Step 3: Save and Close the .env File
After you've added your API keys, save the .env file and close your text editor.

## Important Notes
The .env file should never be uploaded or shared publicly. It contains sensitive information that could be exploited if it falls into the wrong hands. When you are sharing your code or pushing it to a public repository, make sure to add the .env file to your .gitignore file to prevent it from being uploaded.

If you rename your .env file or move it to a different location, you'll need to update the path to the .env file in your Python script.

The Python library python-dotenv is used to load the .env file. Make sure it's installed in your Python environment. You can install it using pip:
```bashCopy code
pip3 install python-dotenv
```

That's it! You've successfully setup your .env file. When you run your Python script, the load_dotenv() function will load your Flickr API Key and Secret Key from the .env file, and they'll be used to authenticate your requests to the Flickr API.

