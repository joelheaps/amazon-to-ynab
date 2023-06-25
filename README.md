# Amazon - to - YNAB

This is a simple tool to automate some of the hassle of matching YNAB (the popular [budgeting app](https://www.ynab.com/)) transactions to Amazon purchases, by adding a memo to each matched transaction in YNAB.

> #### 🛠️ Work in Progress
> I've used this tool myself, and it works, but I plan to tidy it up and add some creature-comforts.

## Getting setup

1. **Install Python 3.**

2. **Clone this repository.**

    ```shell
    git clone https://github.com/joelheaps/amazon-to-ynab
    ```
3. **Create a Python environment (probably).**

    ```shell
    python -m venv ./venv
    source venv/bin/activate
    ```

    Or on Windows:
    ```shell
    python -m venv ./venv
    .\venv\scripts\activate.bat
    ```
4. **Install the prereqs for running this tool.**

   ```shell
   pip install -r requirements.txt
   ```

5. **Get a YNAB personal access token from [https://app.ynab.com/settings/developer](https://app.ynab.com/settings/developer).**
    
    Save it to `config.toml` on the line `ynab.api_token = "your_token_in_quotes_here"`.

6. **If you have multiple budgets, browse to the one you want to match transactions from and copy the budget ID from the URL.**
    
    It's pretty obvious in the URL; grab the "random" text between `https://app.ynab.com/` and `/budget`.  Save it to `config.toml` on the line `ynab.budget_id = "budget_id_in_quotes_here"`.

    > 💡 If you only have one budget, you can also just leave this blank; this tool will attempt to find the default budget on your account.


## Workflow 

1. **Save orders from [https://www.amazon.com/gp/your-account/order-history](https://www.amazon.com/gp/your-account/order-history) to the `orders-html` folder.**
  
    Use multiple files if you want to include more orders (just make sure they have unique names).

2. **Save transactions from [https://www.amazon.com/cpe/yourpayments/transactions](https://www.amazon.com/cpe/yourpayments/transactions) to the `payments-html` folder.**
  
    Again, use multiple files if you'd like.

3. **Run `amazon.py` and then `ynab.py`.**
    
    If everything on the screen checks out, set `dry_run = false` in `config.toml` and run `ynab.py` again.