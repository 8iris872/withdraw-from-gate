# withdraw-from-gate
Вывод с биржи Gate с точными суммами. Токен, сеть, максимальная комиссия и задержки указываются в main в конце файла. Перед выводом 3 раза проверяется комиссия и если все 3 раза комиссия  ниже указанной, то вывод запустится. Сделано из-за того что данные по api передаются с задержкой. Сумму вывода указывать с учетом комиссии.

Withdraw from the Gate Exchange with exact amounts. Token, chain, max fee and latency are specified in main.py at the end of the file. Before withdrawal 3 times the fee is checked and if all 3 times the fee is lower than indicated, the withdrawal will be run. This is due to the fact that the api data is transmitted with a delay. The amount of the withdrawal is given taking into account the fee.
