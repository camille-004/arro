import arro

while True:
    text = input('ARRO | ')
    res, error = arro.run('<stdin>', text)

    if error:
        print(error.as_str())
    else:
        print(res)

