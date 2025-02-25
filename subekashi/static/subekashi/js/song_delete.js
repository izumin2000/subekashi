// TODO checkValidityを利用
function checkDeleteForm() {
    const reasonValue = document.getElementById("reason").value;
    const deleteEle = document.getElementById("deletesubmit");
    deleteEle.disabled = reasonValue == "";
}

window.addEventListener('load', checkDeleteForm);
document.getElementById('reason').addEventListener('input', checkDeleteForm)