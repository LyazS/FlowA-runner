#  如何运行
节点应该存储前置节点的输出handle
前置节点完成后会发出doneEvent事件
后继节点在收集完所有前置的doneEvent事件后，开始寻找前置节点的输出handle的状态
这很重要，是输出handle的状态，而不是节点的状态
因为一个节点可能有多个输出handle