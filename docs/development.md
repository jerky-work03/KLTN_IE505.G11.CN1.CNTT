# Quy tr?nh ph?t tri?n

1. T?o branch/task theo m? k? ho?ch (`W02-N01`, `W05-H02`...).
2. Ch?y unit test v? lint tr??c commit.
3. M?i run l?u commit, config, seed, manifest hash, method/model/prompt version, th?i ?i?m v? predictions t?ng m?u.
4. Ch? ch?n prompt, threshold v? hyperparameter b?ng train/validation; kh?a test tr??c khi ch?y ch?nh.
5. Kh?ng ??a archive m? ??c, API key ho?c output nh?y c?m v?o Git.

```powershell
$env:PYTHONPATH = "$PWD/src"
python -m pytest
python -m ruff check src tests
```
