# FlowA-runner

## 想法
* 后台运行，只需要返回最后结果就行
* 流式运行，前端需要知道后台在运行的所有任务
* 对于不同的电脑/用户的前端，需要知道不同的后台任务
* 用临时用户方式，参考comfyui做法
* 前端打开的时候，读取或者初始化一个临时用户uuid在localstorage里，每次都用它，直到清除掉就重新初始化一个新的
* 前端提交任务的时候设置一个任务uuid，每次重连就按照这两个uuid找后端要任务状态
* 后端只需要维护好任务状态就可以了

## 总结
* 前端第一次打开，初始化用户uuid在localstorage里，后续每次都用它
* 前端提交任务的时候设置一个任务uuid，后端维护好任务状态
* 工作流放在后端文件夹里边，前端需要实现工作流展示和重命名、历史运行记录
* 前端点击工作流则可以读取后端文件然后用fromObject切换
* 每次运行/打开历史记录，则请求后端获取任务状态，看情况再获取SSE

## 前端
顶部中间：工作流选择，点击可以切换工作流，也可以切换历史记录
顶部左侧：自动保存等信息
顶部右侧：按钮组：运行、保存、

打开的时候，
从localstorage里读取用户uuid、读取当前工作流
从后端获取所有工作流名字

# 后续计划
* [ ]操作按键组:工作流管理器、运行、新建、重命名、优化布局
* [o]条件分支
* [o]历史记录状态标记
* [ ]分支聚合节点
* [ ]注释节点
* [ ]工作流导入导出
* [ ]选择性节点上传数据，例如只有输出节点才上传数据到前端，其他的可以不用
* [ ]复制粘贴
* [ ]历史记录中调试节点