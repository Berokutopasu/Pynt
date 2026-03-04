def vulnerable_function():
    return eval("1 + 'a'")

def another_vulnerable_function():
    return exec("print('This is a vulnerability')")