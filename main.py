import requests
import time
import hashlib
import hmac
import json
import uuid
import pandas as pd
import random

# Создаем пустой DataFrame для записи результатов
result_columns = ['Address', 'Status Code', 'Fee', 'Amount']
result_df = pd.DataFrame(columns=result_columns)

def gen_sign(method, url, query_string=None, payload_string=None):
    key = 'API-ключ'  # Вставьте свой API-ключ
    secret = 'API-секрет'  # Вставьте свой API-секрет
    t = str(int(time.time()))
    m = hashlib.sha512()
    m.update((payload_string or "").encode('utf-8'))
    hashed_payload = m.hexdigest()
    s = '%s\n%s\n%s\n%s\n%s' % (method, url, query_string or "", hashed_payload, t)
    sign = hmac.new(secret.encode('utf-8'), s.encode('utf-8'), hashlib.sha512).hexdigest()
    return {'KEY': key, 'Timestamp': t, 'SIGN': sign}

def get_withdraw_fee(currency, chain):
    host = "https://api.gateio.ws"
    prefix = "/api/v4"
    url = '/wallet/withdraw_status'
    query_param = f'currency={currency}&chain={chain}'
    sign_headers = gen_sign('GET', prefix + url, query_param)
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    headers.update(sign_headers)
    r = requests.get(host + prefix + url + '?' + query_param, headers=headers)
    if r.status_code == 200 and isinstance(r.json(), list) and len(r.json()) > 0:
        return float(r.json()[0].get('withdraw_fix_on_chains', {}).get(chain, 0))
    return 0  # В случае отсутствия информации о комиссии

def read_addresses_from_file(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
    addresses = [(line.split(';')[0], float(line.split(';')[1])) for line in lines if line.strip()]
    return addresses

def generate_withdraw_order_id():
    return "order_" + str(int(time.time())) + "_" + str(uuid.uuid4().hex[:6])

def get_balance(currency):
    host = "https://api.gateio.ws"
    prefix = "/api/v4"
    url = '/spot/accounts'
    query_param = f'currency={currency}'
    sign_headers = gen_sign('GET', prefix + url, query_param)
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    headers.update(sign_headers)
    response = requests.get(host + prefix + url + '?' + query_param, headers=headers)
    if response.status_code == 200 and isinstance(response.json(), list) and len(response.json()) > 0:
        available = float(response.json()[0].get('available', 0))
        locked = float(response.json()[0].get('locked', 0))
        return available, locked
    return 0, 0  # В случае ошибки или отсутствия данных

def withdraw_to_addresses_from_file(file_path, currency, memo, chain, max_fee=0.00091, delay_seconds=30, retry_delay=60, max_retries=3):
    available, locked = get_balance(currency)
    print(f"Доступный баланс: {available}, Заморожено: {locked}")

    withdrawal_addresses = read_addresses_from_file(file_path)
    host = "https://api.gateio.ws"
    prefix = "/api/v4"
    global result_df

    for address, amount_to_withdraw in withdrawal_addresses:
        retries = 0
        while retries <= max_retries:
            fees = []
            for _ in range(3):  # Проверяем комиссию три раза
                fee = get_withdraw_fee(currency, chain)
                fees.append(fee)
                print(f"Checked fee: {fee}")
                time.sleep(15)  # Задержка между проверками комиссии

            if all(f <= max_fee for f in fees) and len(set(fees)) == 1:
                total_withdraw = amount_to_withdraw + fee

                if total_withdraw > available:
                    print(f"Not enough funds to withdraw {total_withdraw} ETH including fee {fee}. Available: {available}")
                    break

                withdraw_order_id = generate_withdraw_order_id()
                body = json.dumps({
                    "withdraw_order_id": withdraw_order_id,
                    "currency": currency,
                    "address": address,
                    "amount": f"{amount_to_withdraw:.8f}",
                    "memo": memo,
                    "chain": chain
                })

                sign_headers = gen_sign('POST', prefix + '/withdrawals', '', body)
                headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
                headers.update(sign_headers)

                r = requests.post(host + prefix + '/withdrawals', headers=headers, data=body)
                status_code = r.status_code if r is not None else None

                new_row = pd.DataFrame([{
                    'Address': address,
                    'Status Code': status_code if r is not None else None,
                    'Fee': fee,
                    'Amount': amount_to_withdraw
                }])

                # Проверяем, что новая строка не пуста и не содержит только NA значения
                if not new_row.empty and not new_row.isna().all(axis=1).any():
                    result_df = pd.concat([result_df, new_row], ignore_index=True)
                else:
                    print("Попытка добавить пустую или полностью NA строку; строка не будет добавлена.")

                if r is not None and r.status_code == 200:
                    print(f"Successfully withdrawn {amount_to_withdraw} ETH to {address}")
                    break
                else:
                    print(f"Failed to withdraw to {address} - Status Code: {status_code}, Response: {r.json()}")

                time.sleep(delay_seconds)  # Задержка между выводами
            else:
                print(f"Fee inconsistency detected or fee exceeds max fee. Withdrawal to {address} canceled.")
                retries += 1
                if retries <= max_retries:
                    print(f"Retrying after {retry_delay} seconds...")
                    time.sleep(retry_delay)
            if retries > max_retries:
                print(f"Maximum retries exceeded for {address}. Moving to next address.")
                break

    # Сохраняем DataFrame в CSV файл
    result_df.to_csv('withdraw_results.csv', index=False)

if __name__ == "__main__":
    addresses_file_path = "address.txt"  # Файл с адресами и суммами
    currency = "ETH"
    memo = ""  # Дополнительное поле, может быть использовано или оставлено пустым в зависимости от требований API
    chain = "ETH"  # Сеть для вывода
    delay_seconds = 20  # Задержка между операциями вывода
    max_fee = 0.00091  # Максимально допустимая комиссия

    withdraw_to_addresses_from_file(addresses_file_path, currency, memo, chain, max_fee=max_fee, delay_seconds=delay_seconds)


