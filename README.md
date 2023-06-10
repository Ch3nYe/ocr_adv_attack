# OCR_adv_attack
OCR Adversarial Attack Studing Record
======================================
This project implements the FGSM and PGD attack on OCR in pytorch. And use the crnn model as the target model, the model project could be found in [crnn.pytorch](https://github.com/meijieru/crnn.pytorch).

Attack demo
--------
A demo program can be found in ``FGSM_CRNN.py`` and ``PGD_CRNN.py``. The pretrained model ``crnn.pth`` is in directory ``data/``
Then launch the demo by:

    python FGSM_CRNN.py
    python PGD_CRNN.py


