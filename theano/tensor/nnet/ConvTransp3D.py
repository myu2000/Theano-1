import numpy as N
from theano.tensor import basic as T
from theano.misc import strutil
import theano

class ConvTransp3D(theano.Op):
    """ "Transpose" of Conv3D (Conv3D implements multiplication by an implicitly defined matrix W. This implements multiplication by its transpose) """
    def __eq__(self,other):
        return type(self) == type(other)

    def __hash__(self):
        return hash(type(self))

    def c_code_cache_version(self):
        return (1,)

    def make_node(self, W, b, d, H, RShape = None):
        """
        :param W: Weights, filter
        :param b: bias, shape == (W.shape[0],)
        :param d: strides when moving the filter over the input
        :param H: The output of Conv3D
        """
        W_ = T.as_tensor_variable(W)
        b_ = T.as_tensor_variable(b)
        d_ = T.as_tensor_variable(d)
        H_ = T.as_tensor_variable(H)
        if RShape:
            RShape_ = T.as_tensor_variable(RShape)
        else:
            RShape_ = T.as_tensor_variable([-1,-1,-1])

        return theano.Apply(self, inputs=[W_,b_,d_,H_, RShape_], outputs = [ T.TensorType(H_.dtype, (False,False,False,False,False))() ] )

    def c_compile_args(self):
        flags = ['-Werror']
        return flags


    def infer_shape(self, node, input_shapes):
        W,b,d,H,RShape = node.inputs
        W_shape, b_shape, d_shape, H_shape, RShape_shape = input_shapes
        return [(H_shape[0],  RShape[0], RShape[1], RShape[2], W_shape[4])]

    def grad(self,inputs, output_gradients):
        W,b,d,H, RShape = inputs
        dCdR ,= output_gradients
        dCdH = conv3D( dCdR, W, T.zeros_like(H[0,0,0,0,:]), d)
        WShape = W.shape
        dCdW = convGrad3D(dCdR,d,WShape,H)
        dCdb = T.sum(dCdR,axis=(0,1,2,3))
        dCdd = None #not differentiable, since d is not continuous
        dCdRShape = None #not differentiable, since RShape is not continuous


        if 'name' in dir(dCdR) and dCdR.name is not None:
            dCdR_name = dCdR.name
        else:
            dCdR_name = 'anon'

        if 'name' in dir(H) and H.name is not None:
            H_name = H.name
        else:
            H_name = 'anon'

        if 'name' in dir(W) and W.name is not None:
            W_name = W.name
        else:
            W_name = 'anon'

        if 'name' in dir(b) and b.name is not None:
            b_name = b.name
        else:
            b_name = 'anon'


        dCdW.name = 'ConvTransp3D_dCdW.H='+H_name+',dCdR='+dCdR_name+',W='+W_name
        dCdb.name = 'ConvTransp3D_dCdb.H='+H_name+',dCdR='+dCdR_name+',W='+W_name+',b='+b_name
        dCdH.name = 'ConvTransp3D_dCdH.H='+H_name+',dCdR='+dCdR_name

        return [ dCdW,  dCdb, dCdd, dCdH, dCdRShape ]


    def perform(self, node, inputs, output_storage):
        W, b, d, H, RShape = inputs
        print "\t\t\t\tConvTransp3D python code"
        output_storage[0][0] = computeR(W,b,d,H,RShape)

    def c_code(self, node, nodename, inputs, outputs, sub):
        W, b, d, H, RShape = inputs
        fail = sub['fail']

        R = outputs[0]

        codeSource = """
                    ///////////// < code generated by ConvTransp3D >

                    //printf("\t\t\t\tConvTransp3D c code\\n");

                    //Check dimensionality of inputs
                    if (%(H)s->nd != 5)
                    {
                        PyErr_Format(PyExc_ValueError, "H must be a 5-D tensor but it is %%i-D",%(H)s->nd);
                        %(fail)s
                    }

                    if (%(W)s->nd != 5)
                    {
                         PyErr_Format(PyExc_ValueError, "ConvTransp3D: W must be a 5-D tensor");
                %(fail)s
                    }

                    if (%(b)s->nd != 1)
                    {
                         PyErr_Format(PyExc_ValueError, "ConvTransp3D: b must be a vector");
                         %(fail)s
                    }

                    if (%(d)s->nd != 1)
                    {
                         PyErr_Format(PyExc_ValueError, "ConvTransp3D: d must be a vector");
                         %(fail)s
                    }

                    //Read and check stride arguments
                    if (%(d)s->dimensions[0] != 3)
                    {
                         PyErr_Format(PyExc_ValueError, "ConvTransp3D: 3 stride length arguments expected (for row, col, and time) but %%li were given", (long)%(d)s->dimensions[0] );
                         %(fail)s
                    }

                    { // for fail 1
                         int dr = *(dtype_%(d)s*)PyArray_GETPTR1(%(d)s,0);
                         int dc = *(dtype_%(d)s*)PyArray_GETPTR1(%(d)s,1);
                         int dt = *(dtype_%(d)s*)PyArray_GETPTR1(%(d)s,2);

                         if (dr <= 0 || dc <= 0 || dt <= 0)
                         {
                             PyErr_Format(PyExc_ValueError, "ConvTransp3D: Strides must all be positive but are %%i, %%i, %%i",dr,dc,dt);
                             %(fail)s
                          }


                         //Read and check sizes of inputs

                        { // for fail 2
                            const int batchSize = %(H)s->dimensions[0];
                            const int outputChannels =  %(W)s->dimensions[0];

                            if (%(H)s->dimensions[4] != outputChannels)
                            {
                                PyErr_Format(PyExc_ValueError, "W produces a %%i channel image but the image has %%li channels. W.shape: (%%li, %%li, %%li, %%li, %%li) H.shape: (%%li, %%li, %%li, %%li, %%li)", outputChannels, (long)%(H)s->dimensions[4], (long)%(W)s->dimensions[0], (long)%(W)s->dimensions[1], (long)%(W)s->dimensions[2], (long)%(W)s->dimensions[3], (long)%(W)s->dimensions[4], (long)%(H)s->dimensions[0], (long)%(H)s->dimensions[1], (long)%(H)s->dimensions[2], (long)%(H)s->dimensions[3], (long)%(H)s->dimensions[4]);
                                %(fail)s
                            }

                            { // for fail 3

                                const int inputChannels = %(W)s->dimensions[4];

                                if (%(b)s->dimensions[0] != inputChannels)
                                {
                                    PyErr_Format(PyExc_ValueError, "ConvTransp3D: b operates on a %%li channel image but the image has %%i channels", (long)%(b)s->dimensions[0], inputChannels );
                                    %(fail)s
                                }

                                { // for fail 4

                                const int filterHeight = %(W)s->dimensions[1];
                                const int filterWidth = %(W)s->dimensions[2];
                                const int filterDur = %(W)s->dimensions[3];
                                const int outputHeight = %(H)s->dimensions[1];
                                const int outputWidth = %(H)s->dimensions[2];
                                const int outputDur = %(H)s->dimensions[3];

                                int videoHeight = (outputHeight-1) * dr + filterHeight;
                                int videoWidth = (outputWidth-1) * dc + filterWidth;
                                int videoDur = (outputDur-1) * dt + filterDur;

                                if (%(RShape)s)
                                {
                                    if (%(RShape)s->nd != 1)
                                    {
                                        PyErr_Format(PyExc_ValueError, "ConvTransp3D: RShape must be a vector");
                                        %(fail)s
                                    }

                                    if (%(RShape)s->dimensions[0] != 3)
                                    {
                                        PyErr_Format(PyExc_ValueError, "RShape must specify a 3D shape ( [height,width,duration] )");
                                        %(fail)s
                                    }

                                    dtype_%(RShape)s RShape0 = *(dtype_%(RShape)s*)PyArray_GETPTR1(%(RShape)s,0);
                                    dtype_%(RShape)s RShape1 = *(dtype_%(RShape)s*)PyArray_GETPTR1(%(RShape)s,1);
                                    dtype_%(RShape)s RShape2 = *(dtype_%(RShape)s*)PyArray_GETPTR1(%(RShape)s,2);

                                    if (RShape0 != -1)
                                    {
                                        if (RShape0 < videoHeight || RShape1 < videoWidth || RShape2 < videoDur)
                                        {
                                            PyErr_Format(PyExc_ValueError, "Reconstruction must have physical shape of at least [%%i,%%i,%%i] but RShape argument requests that it be [%%i,%%i,%%i]\\n",videoHeight,videoWidth,videoDur,(int) RShape0,(int) RShape1,(int) RShape2);
                                            %(fail)s
                                        }

                                        videoHeight = RShape0;
                                        videoWidth = RShape1;
                                        videoDur = RShape2;
                                   }
                               } //closes if RShape

                               { // for fail 5

                                   //Allocate the reconstruction
                                   npy_intp dims[5];
                                   dims[0] = batchSize;
                                   dims[4] = inputChannels;
                                   dims[1] = videoHeight;
                                   dims[2] = videoWidth;
                                   dims[3] = videoDur;

                                   if(!(%(R)s) || %(R)s->dimensions[0]!=dims[0] ||
                                    %(R)s->dimensions[1]!=dims[1] ||
                                    %(R)s->dimensions[2]!=dims[2] ||
                                    %(R)s->dimensions[3]!=dims[3] ||
                                    %(R)s->dimensions[4]!=dims[4])
                                   {
                                       Py_XDECREF(%(R)s);
                                       %(R)s = (PyArrayObject *) PyArray_SimpleNew(5, dims, %(H)s->descr->type_num);
                                       if (!(%(R)s)) {
                                           PyErr_Format(PyExc_MemoryError, "ConvTransp3D: could not allocate R");
                                           %(fail)s
                                       }
                                   }

                                   for (int i = 0; i < 3; i++)
                                       if (%(R)s->strides[i] < %(R)s->strides[4])
                                       {
                                           PyErr_Format(PyExc_ValueError, "ConvTransp3D: R must have the smallest stride in its last index, but it doesn't (if this is a problem, the only part of ConvTransp3D that depends on this conditions is the memset, so this is probably easy to fix)");
                                           %(fail)s
                                       }

                                   { // for fail 6


                                       memset(%(R)s->data, 0,  (batchSize-1) * %(R)s->strides[0]+ inputChannels * %(R)s->strides[4] +
                                          (videoHeight-1) * %(R)s->strides[1] +
                                          (videoWidth-1)  * %(R)s->strides[2] +
                                          (videoDur-1)    * %(R)s->strides[3]);



                                       #define ELEM5(x, i,j,k,l,m) * ( dtype_ ## x *) ( x->data + (i)*x->strides[0]+(j)*x->strides[1]+(k)*x->strides[2]+(l)*x->strides[3]+(m)*x->strides[4] )
                                       #define ELEM_AT(x, i) * ( dtype_ ## x *) ( x->data + (i) )



                                       dtype_%(b)s * b = (dtype_%(b)s *) %(b)s->data;

                                       int rs4 = %(R)s->strides[4];
                                       int ws0 = %(W)s->strides[0];
                                       int ws4 = %(W)s->strides[4];
                                       int hs4 = %(H)s->strides[4];

                                       // Compute R
                                       // R[i,r,c,t,j] = b_j + sum_{rc,rk | d \circ rc + rk = r} sum_{cc,ck | ...} sum_{tc,tk | ...} sum_k W[k, rk, ck, tk,j] * H[i,rc,cc,tc,k]

                                       for (int i = 0; i < batchSize; i++) {
                                        for (int r = 0; r < videoHeight; r++) {
                                         const int frc = std::max(0.0, ceil(float(r-filterHeight+1)/float(dr)));
                                         for (int c = 0; c < videoWidth; c++) {
                                          const int fcc = std::max(0.0, ceil(float(c-filterWidth +1)/float(dc)));
                                          for (int t = 0; t < videoDur; t++) {
                                           const int ftc = std::max(0.0, ceil(float(t-filterDur +1)  /float(dt)));

                                           long long Rpost = i * %(R)s->strides[0] + r * %(R)s->strides[1] + c * %(R)s->strides[2] + t * %(R)s->strides[3];

                                           long long Rpos = Rpost;
                                           for (int j = 0; j < inputChannels; j++)
                                           {
                                            //ELEM5(%(R)s, i,r,c,t,j) = b[j];
                                            ELEM_AT(%(R)s,Rpos) = b[j];
                                            Rpos += rs4;
                                           }


                                           for (int rc = frc; rc < outputHeight; rc++) {
                                            const int rk = r - rc * dr;
                                            if (rk < 0) break;

                                            for (int cc = fcc; cc < outputWidth; cc++) {
                                             const int ck = c - cc * dc;
                                             if (ck < 0) break;

                                             for (int tc = ftc; tc < outputDur; tc++)
                                             {
                                              const int tk = t - tc * dt;
                                              if (tk < 0) break;

                                              int Wpos = rk * %(W)s->strides[1] +  ck * %(W)s->strides[2] + tk * %(W)s->strides[3];
                                              int Hpostc = i * %(H)s->strides[0] +      rc * %(H)s->strides[1] +  cc * %(H)s->strides[2] + tc * %(H)s->strides[3];
                                              Rpos = Rpost;
                                              for (int j = 0; j < inputChannels; j++)
                                              {
                                               int Wposj = Wpos;
                                               dtype_%(R)s & writePos = ELEM_AT(%(R)s,Rpos);

                                               int Hpos = Hpostc;

                                               for (int k = 0; k < outputChannels; k++) {
                                                //TODO-- it's probably bad in terms of cache that our inner loop is over the largest stride of W.... maybe OK since it's the smallest stride of H
                                                //writePos += ELEM5(%(W)s,k,rk,ck,tk,j) * ELEM5(%(H)s,i,rc,cc,tc,k);
                                                //writePos += ELEM_AT(%(W)s,Wpos) * ELEM_AT(%(H)s,Hpos);

                                                writePos  += ELEM_AT(%(W)s,Wpos) * ELEM_AT(%(H)s,Hpos);

                                                Wpos += ws0;
                                                Hpos += hs4;

                                               } //close the k loop
                                               Rpos += rs4;
                                               Wpos = Wposj +  ws4;
                                              } //close the j loop
                                             } // close the tc loop
                                            } //cc
                                           } //rc
                                          } //t
                                         } //c
                                        } //r
                                       } //i
                                   } //for fail 6
                               } //for fail 5
                           } //for fail 4
                       } //for fail 3
                   } //for fail 2
               } // for fail 1
               ///////////// < /code generated by ConvTransp3D >
                     """

        return strutil.renderString(codeSource,locals())


convTransp3D = ConvTransp3D()

#If the input size wasn't a multiple of D we may need to cause some automatic padding to get the right size of reconstruction
def computeR(W,b,d,H,Rshape = None):
    assert len(W.shape) == 5
    assert len(H.shape) == 5
    assert len(b.shape) == 1
    assert len(d) == 3


    outputChannels,  filterHeight, filterWidth, filterDur, inputChannels = W.shape
    batchSize, outputHeight, outputWidth, outputDur, outputChannelsAgain = H.shape
    assert outputChannelsAgain == outputChannels
    assert b.shape[0] == inputChannels


    dr,dc,dt = d
    assert dr > 0
    assert dc > 0
    assert dt > 0

    videoHeight = (outputHeight-1) * dr + filterHeight
    videoWidth = (outputWidth-1) * dc + filterWidth
    videoDur = (outputDur-1) * dt + filterDur

    if Rshape is not None and Rshape[0] != -1:
        if Rshape[0] < videoHeight:
            print (Rshape[0], videoHeight)
            assert False
        assert Rshape[1] >= videoWidth
        assert Rshape[2] >= videoDur

        #print "setting video size to Rshape = "+str(Rshape)

        videoHeight, videoWidth, videoDur = Rshape
    #else:
    #       print "No Rshape passed in"

    #print "video size: "+str((videoHeight, videoWidth, videoDur))

    R =  N.zeros( (batchSize, videoHeight,
            videoWidth, videoDur, inputChannels ) , dtype=H.dtype)

    #R[i,j,r,c,t] = b_j + sum_{rc,rk | d \circ rc + rk = r} sum_{cc,ck | ...} sum_{tc,tk | ...} sum_k W[k, j, rk, ck, tk] * H[i,k,rc,cc,tc]
    for i in xrange(0,batchSize):
        #print '\texample '+str(i+1)+'/'+str(batchSize)
        for j in xrange(0,inputChannels):
            #print '\t\tfeature map '+str(j+1)+'/'+str(inputChannels)
            for r in xrange(0,videoHeight):
                #print '\t\t\trow '+str(r+1)+'/'+str(videoHeight)
                for c in xrange(0,videoWidth):
                    for t in xrange(0,videoDur):
                        R[i,r,c,t,j] = b[j]

                        ftc = max([0, int(N.ceil(float(t-filterDur +1  )/float(dt))) ])
                        fcc = max([0, int(N.ceil(float(c-filterWidth +1)/float(dc))) ])

                        rc =  max([0, int(N.ceil(float(r-filterHeight+1)/float(dr))) ])
                        while rc < outputHeight:
                            rk = r - rc * dr
                            if rk < 0:
                                break

                            cc = fcc
                            while cc < outputWidth:
                                ck = c - cc * dc
                                if ck < 0:
                                    break

                                tc = ftc
                                while tc < outputDur:
                                    tk = t - tc * dt
                                    if tk < 0:
                                        break

                                    R[i,r,c,t,j] += N.dot(W[:,rk,ck,tk,j], H[i,rc,cc,tc,:] )

                                    tc += 1
                                "" #close loop over tc
                                cc += 1
                            "" #close loop over cc

                            rc += 1
                        "" #close loop over rc
                    "" #close loop over t
                "" #close loop over c
            "" #close loop over r
        "" #close loop over j
    "" #close loop over i

    return R


from Conv3D import conv3D
from ConvGrad3D import convGrad3D
