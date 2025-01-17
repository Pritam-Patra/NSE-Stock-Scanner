from dateutil.relativedelta import relativedelta, TH
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from .nse_data import NSEData

NSE = NSEData()


def get_next_expiry_date(expiry_type:str = 'weekly'):
    '''
    Get Future and Options Expiry Contracts Date for the next 3 months from TODAY. 
    For Equity, it is on last Trursday of Month and for Nifty-BankNifty it is for Last Thursday of the Week UNTILL or UNLESS it is a Holiday
    args:
        expiry_type: Insert from [monthly, equity, weekly, nifty]
    '''
    today = datetime.today()
    expiry_dates = []

    if expiry_type in ('weekly', 'nifty'):
        for i in range(1,13):
            expiry_dates.append((today + relativedelta(weekday=TH(i))).date().strftime("%d-%b-%Y"))

    elif expiry_type in ('monthly', 'equity'):
        for i in range(1,13):
            x = (today + relativedelta(weekday=TH(i))).date()
            y = (today + relativedelta(weekday=TH(i+1))).date()
            if x.month != y.month :
                if x.day > y.day :
                    expiry_dates.append(x.strftime("%d-%b-%Y"))

    return expiry_dates


def analyse_open_interest(symbol, compare_with:tuple = ('openInterest','changeinOpenInterest','totalTradedVolume'), expiry_dates:tuple = None, top_n:int = 5):
    '''
    Get the Option Chain's Open Interest for analysis. You can read more about it at: https://www.quora.com/How-do-I-read-analyse-the-option-chain-of-a-stock-to-intraday-trade-with-clarity-NSE
    args:
        symbol: NSE Symbol or any Index from the three ['NIFTY','BANKNIFTY','FINNIFTY']
        compare_with: Comapre the Puts Aginst this value. Select From ['openInterest', 'changeinOpenInterest', 'pchangeinOpenInterest','totalTradedVolume', 'totalBuyQuantity', 'totalSellQuantity']
        expiry_dates: List of Expiry dates: in format such as: '29-Nov-2021'. Run FnO.get_next_expiry_date() to get a list of next expiry dates. If None, Nearest Date is used
        top_n: How many top values, EACH of Calls and Put to return
    '''
    if symbol in ['NIFTY','BANKNIFTY','FINNIFTY']:
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
    else:
        url = f'https://www.nseindia.com/api/option-chain-equities?symbol={symbol}'
    
    df_data = {'contract_type':[],'expiryDate': [],'strikePrice':[],'openInterest': [],'changeinOpenInterest': [],'pchangeinOpenInterest': [],'totalTradedVolume': [], 
               'totalBuyQuantity': [], 'totalSellQuantity': []}
    keys = df_data.keys()
    
    r = NSE.get_live_nse_data(url).json()
    data = r['records']['data']

    for entry in data:
        if entry.get('CE'):
            [df_data[name].append(entry['CE'][name]) if name!='contract_type' else df_data['contract_type'].append('Calls_CE') for name in keys]

        if entry.get('PE'):
            [df_data[name].append(entry['PE'][name]) if name!='contract_type' else df_data['contract_type'].append('Puts_PE') for name in keys]
           

    df = pd.DataFrame(df_data)
    df.rename(columns = {'expiryDate':'expiry_date', 'strikePrice':'strike_price'},inplace = True)
    df['expiry_date'] = df['expiry_date'].apply(lambda x:datetime.strptime(x, "%d-%b-%Y").strftime("%d-%b-%Y"))
    df['strike_price'] = df['strike_price'].apply(lambda x: int(x))
    df['absChangeOI'] = df['changeinOpenInterest'].apply(lambda x: abs(x))
    
    # Get specific expiry date
    if not expiry_dates:
        expiry_dates = (df['expiry_date'].min(),) # Single element tuple requires ,
    else:
        expiry_dates = [datetime.strptime(x, "%d-%b-%Y").strftime("%d-%b-%Y") for x in expiry_dates]   
    df = df[df['expiry_date'].isin(expiry_dates)]
    
    # plotting
    length = len(compare_with)
    odd = length%2
    rows = (length//2) + 1 if odd else length//2
    f,ax = plt.subplots(rows,2,figsize = (25,10*rows))
    f.suptitle(f"{symbol} Option Chain Analysis", y = 0.93, fontsize = 17, weight = 600, color = 'teal')
    ax = ax.ravel()
    for i,comp_with in enumerate(compare_with):

        ax[i].set_title(comp_with, pad = 13, fontweight = 500, color = 'blue',fontsize = 15)

        if comp_with == 'changeinOpenInterest':
            topn_df = pd.concat([df[df['contract_type'] == 'Calls_CE'].nlargest(top_n, 'absChangeOI'),df[df['contract_type'] == 'Puts_PE'].nlargest(top_n, 'absChangeOI')])
        else:
            topn_df = pd.concat([df[df['contract_type'] == 'Calls_CE'].nlargest(top_n, comp_with),df[df['contract_type'] == 'Puts_PE'].nlargest(top_n, comp_with)])

        fig = sns.barplot(x="strike_price", y=comp_with, hue="contract_type", data = topn_df, palette = {'Calls_CE': 'tab:green','Puts_PE': 'tab:red'}, ci = None, ax = ax[i])

        for c in fig.containers:
            fig.bar_label(c, fmt='%.0f', label_type='edge', padding=5, color = 'black', fontsize = 15)
            fig.margins(y=0.3)

        fig.set_ylabel(comp_with, labelpad = 10,fontsize = 13)
        fig.set_xlabel('Strike Price (in Rupees)', labelpad = 10, fontsize = 13)
        fig.grid()

    if odd:
        ax[-1].set_axis_off()

    return df