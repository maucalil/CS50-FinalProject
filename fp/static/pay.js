document.querySelector('#name').onclick = function() {
    if (document.querySelector('#name').value !== '') {
        document.querySelector('#submit').disabled = false;
    }
};