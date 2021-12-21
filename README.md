# li-wen

#### 介绍
一款为OBS构建系统设置的自动管理（扩展和释放）worker资源的工具

#### 软件架构
aarch64 和 x86_64


#### 安装教程

1.  clone 仓库到/usr/目录；
2.  将wsdm.service文件拷贝到 /usr/lib/systemd/system, 并在Environment中配置IAM_PASSWORD、IAM_USER和IAM_DOMAIN(与对接云资源厂商的基础设施团队确认，当前是华为云)；
3.  配置excluded_workers.yaml，格式如文件中所示；

#### 使用说明

1.  启动：systemctl start wsdm
2.  停止: systemctl stop wsdm


#### 参与贡献

1.  Fork 本仓库
2.  新建 Feat_xxx 分支
3.  提交代码
4.  新建 Pull Request


#### 特技

1.  使用 Readme\_XXX.md 来支持不同的语言，例如 Readme\_en.md, Readme\_zh.md
2.  Gitee 官方博客 [blog.gitee.com](https://blog.gitee.com)
3.  你可以 [https://gitee.com/explore](https://gitee.com/explore) 这个地址来了解 Gitee 上的优秀开源项目
4.  [GVP](https://gitee.com/gvp) 全称是 Gitee 最有价值开源项目，是综合评定出的优秀开源项目
5.  Gitee 官方提供的使用手册 [https://gitee.com/help](https://gitee.com/help)
6.  Gitee 封面人物是一档用来展示 Gitee 会员风采的栏目 [https://gitee.com/gitee-stars/](https://gitee.com/gitee-stars/)
