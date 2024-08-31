#!/bin/bash

# ポート5000を使用しているプロセスのPIDを取得
PID=$(lsof -t -i:5000)

if [ -n "$PID" ]; then
  echo "ポート5000を使用しているプロセスのPID: $PID"
  
  # プロセスを終了
  kill -9 $PID
  
  echo "ポート5000を解放しました。"
else
  echo "ポート5000を使用しているプロセスはありません。"
fi
