window.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('form');
    const submitButton = form.querySelector('input[type="submit"]');
    const aliasTypeSelect = document.getElementById('alias_type');
    const descriptionEl = document.getElementById('alias-type-description-text');
    const descriptionIconEl = document.getElementById('alias-type-description-icon');

    function updateSubmitState() {
        submitButton.disabled = !form.checkValidity();
    }

    function updateAliasTypeDescription() {
        const selected = aliasTypeSelect.selectedOptions[0];
        const description = selected ? (selected.dataset.description || '') : '';
        descriptionEl.textContent = description;
        // 「選択してください」（value=""）の間はアイコンも非表示にする
        descriptionIconEl.style.display = description ? '' : 'none';
    }

    form.addEventListener('input', updateSubmitState);
    form.addEventListener('change', updateSubmitState);
    aliasTypeSelect.addEventListener('change', updateAliasTypeDescription);

    updateSubmitState();
    updateAliasTypeDescription();
});
