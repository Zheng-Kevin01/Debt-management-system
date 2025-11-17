# Debt-management-system 
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rcParams
from tkinter import *
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
import os

# -------------------------------
# 中文顯示設定
# -------------------------------
rcParams['font.sans-serif'] = ['Microsoft JhengHei']
rcParams['axes.unicode_minus'] = False

# -------------------------------
# 債務資料初始化
# -------------------------------
columns = ['債務名稱', '債權人', '金額', '利率(%)', '到期日(YYYY-MM-DD)', '是否銷帳']
if os.path.exists('debt_data.xlsx'):
    df = pd.read_excel('debt_data.xlsx')
else:
    df = pd.DataFrame(columns=columns)

# 添加 UID 欄位（如果沒有的話）
if 'UID' not in df.columns:
    df['UID'] = range(1, len(df)+1)

# -------------------------------
# 月收入初始化與讀取
# -------------------------------
income_file = 'income.txt'
income = 0
if os.path.exists(income_file):
    try:
        with open(income_file, 'r') as f:
            income = float(f.read())
    except:
        income = 0

# -------------------------------
# GUI 主視窗
# -------------------------------
root = Tk()
root.title("債務管理系統v1.5.0")
root.geometry("1400x650")

tree = ttk.Treeview(root, columns=['TAG'] + columns + ['風險指數'], show='headings')
tree.heading('TAG', text='TAG')
for col in columns + ['風險指數']:
    tree.heading(col, text=col)
tree.pack(fill=BOTH, expand=True)

budget_label = Label(root, text="", font=("微軟正黑體", 12))
budget_label.pack(pady=5)

# -------------------------------
# 風險計算函式
# -------------------------------
def calculate_risk(row):
    if str(row['是否銷帳']).lower() in ['是', 'yes']:
        return 0
    try:
        days_to_due = (pd.to_datetime(row['到期日(YYYY-MM-DD)']) - datetime.today()).days
        if days_to_due < 0:
            days_to_due = 0
    except:
        days_to_due = 30
    urgency_factor = 1 + (30 / (days_to_due + 1))**1.2
    risk_index = row['金額'] * row['利率(%)'] / 100 * urgency_factor
    return round(risk_index, 2)

# -------------------------------
# 樹狀圖刷新函式 -風險指數排序-
# -------------------------------
def refresh_tree():
    for i in tree.get_children():
        tree.delete(i)
    if df.empty:
        budget_label.config(text="尚無債務資料")
        return

    df['風險指數'] = df.apply(calculate_risk, axis=1).round(2)
    mean_risk = df['風險指數'].mean()

    def risk_level(val):
        if val > mean_risk * 1.5:
            return 'high'
        elif val >= mean_risk:
            return 'mid'
        else:
            return 'low'
    df['風險等級'] = df['風險指數'].apply(risk_level)

    df_sorted = df.sort_values(by='風險指數', ascending=False).reset_index(drop=True)

    tree.tag_configure('high_risk', background='#FF6347')
    tree.tag_configure('mid_risk', background='#FFD700')
    tree.tag_configure('low_risk', background='#32CD32')

    for _, row in df_sorted.iterrows():
        if row['風險等級'] == 'high':
            flag, tag = '🚩', 'high_risk'
        elif row['風險等級'] == 'mid':
            flag, tag = '⚠️', 'mid_risk'
        else:
            flag, tag = '✅', 'low_risk'

        formatted_amount = f"{row['金額']:,.0f}"
        formatted_rate = f"{row['利率(%)']:.2f}%"
        formatted_risk = f"{row['風險指數']:.2f}"

        tree.insert('', 'end', iid=str(row['UID']),
                    values=[flag, row['債務名稱'], row['債權人'],
                            formatted_amount, formatted_rate,
                            row['到期日(YYYY-MM-DD)'], row['是否銷帳'], formatted_risk],
                    tags=(tag,))

    total_debt = df['金額'].sum()
    available = income - total_debt
    color = "green" if available >= 0 else "red"
    budget_label.config(
        text=f"收入: {income:,g}   債務總額: {total_debt:,g}   可運用資金: {available:,g}",
        fg=color
    )

refresh_tree()

# -------------------------------
# 收入輸入 GUI
# -------------------------------
def input_income_gui():
    global income
    try:
        val = simpledialog.askfloat("收入輸入", "請輸入目前收入:", initialvalue=income)
        if val is not None:
            income = val
            with open(income_file, 'w') as f:
                f.write(str(income))
            messagebox.showinfo("完成", f"已設定收入: {income}")
            refresh_tree()
    except Exception as e:
        messagebox.showerror("錯誤", f"輸入格式錯誤: {e}")

# -------------------------------
# 新增債務表單
# -------------------------------
def add_debt_form():
    global df
    form = Toplevel(root)
    form.title("新增債務")
    entries = {}
    for i, text in enumerate(columns):
        Label(form, text=text).grid(row=i, column=0, padx=5, pady=5)
        e = Entry(form)
        e.grid(row=i, column=1, padx=5, pady=5)
        entries[text] = e

    def submit():
        try:
            new_data = [entries[col].get() for col in columns]
            new_data[2] = float(new_data[2])
            new_data[3] = float(new_data[3])
            new_uid = df['UID'].max() + 1 if not df.empty else 1
            new_data.append(new_uid)
            df = pd.concat([df, pd.DataFrame([new_data], columns=columns + ['UID'])], ignore_index=True)
            refresh_tree()
            form.destroy()
        except Exception as e:
            messagebox.showerror("錯誤", f"輸入格式有誤: {e}")

    Button(form, text="確認", width=12, command=submit).grid(row=len(columns), column=0, pady=10)
    Button(form, text="取消", width=12, command=form.destroy).grid(row=len(columns), column=1, pady=10)

# -------------------------------
# 刪除債務
# -------------------------------
def delete_debt_gui():
    global df
    selected = tree.selection()
    if selected:
        uid = int(selected[0])
        idx = df[df['UID'] == uid].index[0]
        df = df.drop(index=idx)
        refresh_tree()
    else:
        messagebox.showwarning("警告", "請選擇要刪除的債務!")

# -------------------------------
# 修改債務
# -------------------------------
def modify_debt_gui():
    global df
    selected = tree.selection()
    if selected:
        uid = int(selected[0])
        idx = df[df['UID'] == uid].index[0]
        form = Toplevel(root)
        form.title("修改債務")
        entries = {}
        for i, col in enumerate(columns):
            Label(form, text=col).grid(row=i, column=0, padx=5, pady=5)
            e = Entry(form)
            e.grid(row=i, column=1, padx=5, pady=5)
            e.insert(0, str(df.at[idx, col]))
            entries[col] = e

        def submit():
            try:
                for col in columns:
                    val = entries[col].get()
                    if col in ['金額', '利率(%)']:
                        val = float(val)
                    df.at[idx, col] = val
                refresh_tree()
                form.destroy()
            except Exception as e:
                messagebox.showerror("錯誤", f"輸入格式有誤: {e}")

        Button(form, text="確認", width=12, command=submit).grid(row=len(columns), column=0, pady=10)
        Button(form, text="取消", width=12, command=form.destroy).grid(row=len(columns), column=1, pady=10)
    else:
        messagebox.showwarning("警告", "請選擇要修改的債務!")

# -------------------------------
# 風險分析 GUI
# -------------------------------
def risk_analysis_gui():
    if df.empty:
        messagebox.showinfo("風險分析", "沒有債務資料")
        return
    mean_risk = df['風險指數'].mean()
    high_risk = df[df['風險指數'] > mean_risk * 1.5]
    mid_risk = df[(df['風險指數'] >= mean_risk) & (df['風險指數'] <= mean_risk * 1.5)]
    low_risk = df[df['風險指數'] < mean_risk]

    msg = f"💰 目前收入: {income}\n\n"

    if not high_risk.empty:
        msg += "🚩【高風險債務】\n"
        msg += "\n".join([f"{r['債務名稱']} - 風險指數: {r['風險指數']:.2f}" for _, r in high_risk.iterrows()]) + "\n\n"
    else:
        msg += "🚩【高風險債務】無\n\n"

    if not mid_risk.empty:
        msg += "⚠️【中風險債務】\n"
        msg += "\n".join([f"{r['債務名稱']} - 風險指數: {r['風險指數']:.2f}" for _, r in mid_risk.iterrows()]) + "\n\n"
    else:
        msg += "⚠️【中風險債務】無\n\n"

    if not low_risk.empty:
        msg += "✅【低風險債務】\n"
        msg += "\n".join([f"{r['債務名稱']} - 風險指數: {r['風險指數']:.2f}" for _, r in low_risk.iterrows()])
    else:
        msg += "✅【低風險債務】無"

    messagebox.showinfo("風險分析結果", msg)

# -------------------------------
# 生成報表 GUI
# -------------------------------
def generate_report_gui():
    if df.empty:
        messagebox.showinfo("報表生成", "沒有債務資料可生成報表")
        return

    df['風險指數'] = df.apply(calculate_risk, axis=1).round(2)
    mean_risk = df['風險指數'].mean()

    def risk_level(val):
        if val > mean_risk * 1.5:
            return 'high'
        elif val >= mean_risk:
            return 'mid'
        else:
            return 'low'
    df['風險等級'] = df['風險指數'].apply(risk_level)

    df_sorted = df.sort_values(by='風險指數', ascending=False).reset_index(drop=True)
    total_amount = df_sorted['金額'].sum()

    # Excel 報表
    with pd.ExcelWriter('債務報表.xlsx', engine='xlsxwriter') as writer:
        df_report = df_sorted.copy()
        df_report['TAG'] = df_report['風險等級'].map({'high':'🚩','mid':'⚠️','low':'✅'})
        df_report['金額'] = df_report['金額'].apply(lambda x: f"{x:,.0f}")
        df_report['利率(%)'] = df_report['利率(%)'].apply(lambda x: f"{x:.2f}")
        df_report['風險指數'] = df_report['風險指數'].apply(lambda x: f"{x:.2f}")
        df_report.to_excel(writer, index=False, sheet_name='債務明細',
                           columns=['TAG'] + columns + ['風險指數'])
        workbook  = writer.book
        worksheet = writer.sheets['債務明細']
        row_max = len(df_report) + 2
        worksheet.write(row_max, 3, f"總金額: {total_amount:,g}")
        worksheet.write(row_max+1, 3, f"收入: {income:,g}")
        worksheet.write(row_max+2, 3, f"報表生成日期: {datetime.today().strftime('%Y-%m-%d')}")

    # 風險排序圖
    plt.figure(figsize=(10,6))
    plt.bar(df_sorted['債務名稱'], df_sorted['風險指數'], color='tomato')
    import matplotlib.ticker as mtick
    plt.gca().yaxis.set_major_formatter(mtick.StrMethodFormatter('{x:,.0f}'))
    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.title('各債務風險指數排序（高 → 低）', fontsize=14)
    plt.ylabel('風險指數', fontsize=12)
    plt.tight_layout()
    plt.savefig('債務風險排序圖.png')
    plt.show()

    # 分布圖
    df.plot(kind='bar', x='債務名稱', y='金額', title='債務金額分佈')
    plt.gca().yaxis.set_major_formatter(mtick.StrMethodFormatter('{x:,.0f}'))
    plt.tight_layout()
    plt.savefig('債務分布圖.png')
    plt.show()

    messagebox.showinfo("報表生成", "債務報表/風險圖表/分布圖產生成功！")

# -------------------------------
# GUI 按鈕
# -------------------------------
frame = Frame(root)
frame.pack(pady=10)

Button(frame, text="新增債務", width=12, command=add_debt_form).grid(row=0, column=0, padx=5)
Button(frame, text="刪除債務", width=12, command=delete_debt_gui).grid(row=0, column=1, padx=5)
Button(frame, text="修改債務", width=12, command=modify_debt_gui).grid(row=0, column=2, padx=5)
Button(frame, text="收入輸入", width=12, command=input_income_gui).grid(row=0, column=3, padx=5)
Button(frame, text="風險分析", width=12, command=risk_analysis_gui).grid(row=0, column=4, padx=5)
Button(frame, text="生成報表", width=12, command=generate_report_gui).grid(row=0, column=5, padx=5)

# -------------------------------
# 關閉時自動保存
# -------------------------------
def on_closing():
    if messagebox.askokcancel("離開", "是否要保存資料並退出?"):
        df.to_excel('debt_data.xlsx', index=False)
        root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()
