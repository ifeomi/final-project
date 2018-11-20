let form = document.querySelector("#register-form");
let username = document.querySelector("#username");
form.onsubmit = function(e) {
    e.preventDefault();
    $.get("/check", {username: username.value}, function(data){
        if (data) {
            form.submit();
        }
        else {
            alert("Username is taken");
        }
    })
}