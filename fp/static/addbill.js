document.querySelector('#name').onkeyup = function () {
    if(document.querySelector('#name').value === '') {
        document.querySelector('#submit').disabled = true;
    }
};

document.querySelector('#price').onkeyup = function () {
    if(document.querySelector('#price').value === '') {
        document.querySelector('#submit').disabled = true;
    }
    else {
        document.querySelector('#submit').disabled = false;
    }
};

