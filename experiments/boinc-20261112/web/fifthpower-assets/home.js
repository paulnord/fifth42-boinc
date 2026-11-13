const copyButton = document.getElementById('copy-project');
copyButton.addEventListener('click', async () => {
  const field = document.getElementById('project-address');
  const status = document.getElementById('copy-status');
  try {
    if (!navigator.clipboard) throw new Error('Select the address to copy');
    await navigator.clipboard.writeText(field.value);
    status.textContent = 'Project URL copied. Keep your existing tunnel open.';
    copyButton.textContent = 'Copied';
  } catch {
    field.focus();
    field.select();
    status.textContent = 'Address selected. Press Command-C or Control-C to copy.';
  }
});
