from terabox import terabox

def test_cookies():
    print("Testing Cookies Loading...")
    try:
        cookies = terabox.get_cookies_dict()
        print(f"Loaded {len(cookies)} cookies.")
        if len(cookies) > 0:
            print("Cookies loaded successfully.")
        else:
            print("Warning: No cookies found.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_cookies()
