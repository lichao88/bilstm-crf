#coding:utf-8
__author__ = 'jmh081701'
import  tensorflow as tf
from  baseTool import DATA_PREPROCESS
from tensorflow.contrib import  crf
import  numpy as np

def viterbi_decode(score, transition_params,supervised_y=None):
      """Decode the highest scoring sequence of tags outside of TensorFlow.
        修改crf里面的源码,本函数支持一个batch一个batch的解码
      """
      global sequence_length
      shape = np.shape(score)
      viterbis=[]
      right_rate =0
      for i in range(shape[0]):
          viterbi=crf.viterbi_decode(score[i],transition_params[i])
          viterbis.append(viterbi)

      if True:
          #测试命名实体的准确率:看有多少个实体名称被识别出来
          namely_set_supervise=set()
          namely_set_predict=set()
          #先计算各个位置的预测结果
          total_cnt =0
          right_cnt =0

          for simple_index in range(np.shape(supervised_y)[0]):
                for col_index in range(np.shape(supervised_y)[1]):
                    if supervised_y[simple_index,col_index]==viterbis[simple_index][0][col_index]:

                        right_cnt+=1
                    total_cnt+=1
          right_rate = right_cnt/total_cnt
      return viterbis,right_rate
def lstm(x,A,W):
    with tf.name_scope("lstm"):
        x=tf.reshape(x,shape=[batch_size,sequence_length,frame_size])
        rnn_cell_fw=tf.nn.rnn_cell.LSTMCell(hidden_num)
        #前向RNN
        rnn_cell_bw=tf.nn.rnn_cell.LSTMCell(hidden_num)
        #后向RNN
        # 其实这是一个双向深度RNN网络,对于每一个长度为n的序列[x1,x2,x3,...,xn]的每一个xi,都会在深度方向跑一遍RNN,跑上hidden_num个隐层单元
        output,states=tf.nn.bidirectional_dynamic_rnn(rnn_cell_fw,rnn_cell_bw,x,dtype=tf.float32)
        #注意output有两部分：output_fw和output_bw.
        #states这个中间状态输出不管
        #将output[0]和Output[1]拼接在一起
        fw_output = output[0][:,:,:] #output[0]的形状：[batch_size, max_time, cell_fw.output_size]
        # 所以 取各个batch,各个时间步里面的最后一个隐藏层的输出.
        bw_output = output[1][:,:,:] #与fw_output同理
        #各项拼接
        output=tf.concat([fw_output,bw_output],2)#[batch_size,sequence_length,2]
        print(output)
        P= tf.tanh(tf.matmul(output,W),name="P")#[batch_size,sequence_length,num_tags]每个P[i]就是一个序列的P矩阵
        #这个P矩阵就是将来需要丢到crf里面的输入之一
        return P

dataGenerator = DATA_PREPROCESS(train_data="data/source_data.txt",train_label="data/source_label.txt",
                         test_data="data/tes_datat.txt",test_label="data/test_label.txt",
                         embedded_words="data/source_data.txt.ebd.npy",
                         vocb="data/source_data.txt.vab"
                    )
train_rate=0.001
train_step=100
batch_size=2
display_step=10

#每个词的词向量的长度
frame_size=dataGenerator.embedding_vec_length
#每个序列的长度,每句话的长度不定
sequence_length=dataGenerator.sequence_length

#前向和后向的LSTM 都是一层的
hidden_num=1
num_tags=dataGenerator.state_nums

#定义输入,输出,注意序列的长度是变化的。
x=tf.placeholder(dtype=tf.float32,shape=[None],name="inputx")
y=tf.placeholder(dtype=tf.int32,shape=[None,None],name="expected_y")
seq_lengths = tf.placeholder(dtype=tf.int32,shape=[None],name="batch_sequencelengths") #专门提供给crf使用的
#定义P,A矩阵;
# P矩阵形状: 词的个数 X 状态数目:这个矩阵是计算出来的结果,不是以单独的矩阵出现的
# A矩阵形状: 状态数目 X 状态数目
A=tf.Variable(tf.truncated_normal(stddev=0.1,shape=[num_tags,num_tags]))
#W矩阵,bi-LSTM 的每个时间步乘以W
W=tf.Variable(tf.truncated_normal(stddev=0.1,shape=[batch_size,2,num_tags]))

#生成bi-lstm网络
pred_p=lstm(x,A,W)
#crf的log似然损失函数
print(x)
print(A)
print(pred_p)
cost,A=crf.crf_log_likelihood(inputs=pred_p,tag_indices=y,sequence_lengths=seq_lengths,transition_params=A)
train=tf.train.AdamOptimizer(train_rate).minimize(-cost)

sess=tf.Session()
sess.run(tf.initialize_all_variables())
step=1
while step<train_step:
    batch_x,batch_y,batch_seq_lengths=dataGenerator.next_train_batch(batch_size)
#   batch_x=tf.reshape(batch_x,shape=[batch_size,sequence_length,frame_size])
    _loss,__=sess.run([cost,train],feed_dict={x:batch_x,y:batch_y,seq_lengths:batch_seq_lengths})
    if step % display_step ==0:
        #计算一波正确率
        valid_x ,valid_y,batch_seq_lengths = dataGenerator.next_valid_batch(batch_size)
        scores,transition_parameter = sess.run([pred_p,A],feed_dict={x:valid_x,y:valid_y,seq_lengths:batch_seq_lengths})
        viterbi,right_rate = viterbi_decode(scores,transition_parameter,supervised_y=valid_y)
        print({"step":step,"right_rate":right_rate})
    step+=1
