### 网络配置

```shell
git config --global http.proxy http://127.0.0.1:7890 && git config --global https.proxy http://127.0.0.1:7890
```

```shell
git remote -v
git remote set-url origin https://github.com/l00jj/LocalASR.git
```

```shell
# 账号密码缓存一天
git config --global credential.helper 'cache --timeout=86400'

# 取消代理
git config --global --unset http.proxy && git config --global --unset https.proxy
```